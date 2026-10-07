"""
Migração de corte único do Hamilton antigo → Hamilton 2.0 (D6, decisões #8/#20).

RECORTE (decidido 07/10/2026 com o cliente): traz só os **terapeutas que operam
de verdade** e os **pacientes deles**. "Operante" = terapeuta `is_active` que
cadastrou agenda (tem HorarioDisponivel), MENOS 3 terapeutas falsos conhecidos
(ids 12, 30, 81 — Diogo, Elisa, Rebeca). Deu 23 terapeutas e 132 pacientes
(ATIVO + AGUARDANDO_INICIO como ativos; PAUSADO como inativo). Users/Associados
vêm só desses 23. Abordagens e Tags vêm inteiras (são referência pequena).

Gestores: NÃO herdam o `is_staff` do banco antigo (está defasado). Todos entram
como não-staff; o Alan marca `is_staff` manualmente no go-live (decisão #17).

Lê o banco do Hamilton antigo por uma conexão de somente leitura
(`DATABASES['legado']`, ligada por `LEGADO_DATABASE_URL`). Os IDs (`pk_*`) são
preservados, então os vínculos User↔Associado↔Terapeuta continuam válidos.

Uso:
    python manage.py migrar_hamilton            # DRY-RUN (padrão): não grava nada
    python manage.py migrar_hamilton --executar # grava de verdade
"""
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import connection, connections, transaction
from django.contrib.auth.models import User

from principais.models import (
    Abordagem, Associado, HorarioDisponivel, Paciente, Tag, Terapeuta,
)

# Terapeutas "falsos" a excluir do recorte (decidido com o cliente).
EXCLUIR_TERAPEUTAS = {12, 30, 81}
# Status do paciente antigo que viram is_active=True no 2.0 (o resto, inativo).
STATUS_ATIVO = ('ATIVO', 'AGUARDANDO_INICIO')


def _dictfetchall(cursor):
    cols = [c[0] for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def _in(ids):
    """Monta uma cláusula IN segura a partir de uma coleção de inteiros."""
    ids = [int(i) for i in ids]
    return f"({','.join(str(i) for i in ids)})" if ids else "(NULL)"


class Command(BaseCommand):
    help = "Migra o recorte operante (23 terapeutas + pacientes) do Hamilton antigo."

    def add_arguments(self, parser):
        parser.add_argument(
            '--executar', action='store_true',
            help="Grava de verdade. Sem esta flag, roda em dry-run (não grava).",
        )

    def handle(self, *args, **opts):
        self.dry = not opts['executar']
        if 'legado' not in connections.databases:
            raise CommandError(
                "Conexão 'legado' não configurada. Defina LEGADO_DATABASE_URL "
                "apontando para o banco do Hamilton antigo."
            )
        modo = self.style.WARNING("DRY-RUN (nada será gravado)") if self.dry \
            else self.style.ERROR("EXECUÇÃO REAL (gravando no banco do 2.0)")
        self.stdout.write(f"Modo: {modo}")

        leg = connections['legado'].cursor()
        try:
            if self.dry:
                self._migrar(leg)
            else:
                with transaction.atomic():
                    self._migrar(leg)
        finally:
            leg.close()

        self.stdout.write(self.style.SUCCESS(
            "Dry-run concluído (nada gravado)." if self.dry else "Migração concluída."
        ))

    # ------------------------------------------------------------------ escopo
    def _definir_escopo(self, leg):
        """Resolve o recorte: 23 terapeutas operantes + seus associados/users."""
        leg.execute(
            "SELECT t.pk_terapeuta, t.fk_associado FROM terapeutas t "
            "WHERE t.is_active AND EXISTS (SELECT 1 FROM principais_horariodisponivel h "
            "WHERE h.fk_terapeuta_id = t.pk_terapeuta)"
        )
        rows = _dictfetchall(leg)
        self.terapeuta_pks = [
            r['pk_terapeuta'] for r in rows
            if r['pk_terapeuta'] not in EXCLUIR_TERAPEUTAS
        ]
        self.associado_pks = {
            r['fk_associado'] for r in rows
            if r['pk_terapeuta'] not in EXCLUIR_TERAPEUTAS and r['fk_associado']
        }
        # Users dos associados do recorte.
        leg.execute(
            f"SELECT usuario_id FROM associados WHERE pk_associado IN {_in(self.associado_pks)} "
            f"AND usuario_id IS NOT NULL"
        )
        self.user_ids = {r['usuario_id'] for r in _dictfetchall(leg)}
        self.stdout.write(self.style.SUCCESS(
            f"Recorte: {len(self.terapeuta_pks)} terapeutas, "
            f"{len(self.associado_pks)} associados, {len(self.user_ids)} users."
        ))

    # ------------------------------------------------------------------ passos
    def _migrar(self, leg):
        self._definir_escopo(leg)
        self._migrar_users(leg)
        self._migrar_associados(leg)
        self._migrar_abordagens(leg)
        self._migrar_tags(leg)
        self._migrar_terapeutas(leg)
        self._migrar_supervisores(leg)
        self._migrar_m2m_tags(leg)
        self._migrar_horarios(leg)
        self._migrar_pacientes(leg)
        # Todas as PKs vieram explícitas; reseta as sequences para o app em
        # produção inserir novos registros sem colidir.
        from principais.models import SessaoSemanal
        self._reset_seqs([User, Associado, Abordagem, Tag, Terapeuta,
                          HorarioDisponivel, Paciente, SessaoSemanal])
        if not self.dry:
            self.stdout.write("  Sequences resetadas (Postgres).")

    def _n(self, rotulo, qtd):
        self.stdout.write(f"  {rotulo}: {qtd}")

    def _reset_seqs(self, models):
        """No Postgres, inserir PKs explícitas não avança a sequence — reseta
        para MAX(pk)+1 para o app poder inserir novas linhas sem colidir.
        No-op no SQLite."""
        if self.dry or connection.vendor != 'postgresql':
            return
        for sql in connection.ops.sequence_reset_sql(no_style(), models):
            connection.cursor().execute(sql)

    def _migrar_users(self, leg):
        leg.execute(
            "SELECT id, password, last_login, is_superuser, username, first_name, "
            f"last_name, email, is_active, date_joined FROM auth_user WHERE id IN {_in(self.user_ids)}"
        )
        rows = _dictfetchall(leg)
        self._n("Users lidos (recorte)", len(rows))
        if self.dry:
            return
        for r in rows:
            # password é o HASH cru. is_staff/is_superuser ZERADOS: gestores são
            # marcados manualmente no go-live (decisão #17).
            User.objects.update_or_create(
                id=r['id'],
                defaults=dict(
                    password=r['password'], last_login=r['last_login'],
                    is_superuser=False, username=r['username'],
                    first_name=r['first_name'] or '', last_name=r['last_name'] or '',
                    email=r['email'] or '', is_staff=False,
                    is_active=r['is_active'], date_joined=r['date_joined'],
                ),
            )

    def _migrar_associados(self, leg):
        leg.execute(
            "SELECT pk_associado, nome, email, telefone, contato_apoio, "
            "dat_nascimento, sexo, cpf, endereco, is_active, observacao, usuario_id "
            f"FROM associados WHERE pk_associado IN {_in(self.associado_pks)}"
        )
        rows = _dictfetchall(leg)
        self._n("Associados lidos (recorte)", len(rows))
        if self.dry:
            return
        for r in rows:
            Associado.objects.update_or_create(
                pk_associado=r['pk_associado'],
                defaults=dict(
                    nome=r['nome'], email=r['email'], telefone=r['telefone'],
                    contato_apoio=r['contato_apoio'], dat_nascimento=r['dat_nascimento'],
                    sexo=r['sexo'], cpf=r['cpf'] or None, endereco=r['endereco'],
                    is_active=r['is_active'], observacao=r['observacao'],
                    usuario_id=r['usuario_id'],
                ),
            )

    def _migrar_abordagens(self, leg):
        leg.execute("SELECT pk_abordagem, abordagem FROM abordagens")
        rows = _dictfetchall(leg)
        self._n("Abordagens lidas", len(rows))
        if self.dry:
            return
        for r in rows:
            Abordagem.objects.update_or_create(
                pk_abordagem=r['pk_abordagem'], defaults=dict(abordagem=r['abordagem']),
            )

    def _migrar_tags(self, leg):
        leg.execute("SELECT pk_tag, nome FROM tags")
        rows = _dictfetchall(leg)
        self._n("Tags lidas", len(rows))
        if self.dry:
            return
        for r in rows:
            Tag.objects.update_or_create(pk_tag=r['pk_tag'], defaults=dict(nome=r['nome']))
        # Avança a sequence após as PKs explícitas, senão o get_or_create abaixo
        # tenta reusar pk=1 e colide (Postgres).
        self._reset_seqs([Tag])
        # Tags-chave do 2.0 (decisões #5/#7).
        for nome in ('supervisor', 'prefeitura'):
            Tag.objects.get_or_create(nome=nome)

    def _migrar_terapeutas(self, leg):
        leg.execute(
            "SELECT pk_terapeuta, fk_associado, fk_abordagem, pacientes_max, "
            f"is_active, observacao, link_agenda FROM terapeutas "
            f"WHERE pk_terapeuta IN {_in(self.terapeuta_pks)}"
        )
        rows = _dictfetchall(leg)
        self._n("Terapeutas lidos (recorte)", len(rows))
        if self.dry:
            return
        for r in rows:
            Terapeuta.objects.update_or_create(
                pk_terapeuta=r['pk_terapeuta'],
                defaults=dict(
                    fk_associado_id=r['fk_associado'], fk_abordagem_id=r['fk_abordagem'],
                    pacientes_max=r['pacientes_max'], is_active=r['is_active'],
                    observacao=r['observacao'], link_agenda=r['link_agenda'],
                    fk_supervisor=None,
                ),
            )

    def _migrar_supervisores(self, leg):
        """`fk_decano` (Associado) → `fk_supervisor` (Terapeuta), só quando o
        supervisor também está no recorte. Marca o supervisor com a tag."""
        leg.execute(
            f"SELECT pk_terapeuta, fk_decano FROM terapeutas "
            f"WHERE pk_terapeuta IN {_in(self.terapeuta_pks)} AND fk_decano IS NOT NULL"
        )
        rows = _dictfetchall(leg)
        self._n("Terapeutas com decano (recorte)", len(rows))
        if self.dry:
            return
        assoc_para_terapeuta = {
            t.fk_associado_id: t.pk_terapeuta for t in Terapeuta.objects.all()
        }
        tag_sup, _ = Tag.objects.get_or_create(nome='supervisor')
        supervisores_pk = set()
        for r in rows:
            sup_pk = assoc_para_terapeuta.get(r['fk_decano'])
            if not sup_pk:
                continue  # decano fora do recorte → fica sem supervisor
            Terapeuta.objects.filter(pk_terapeuta=r['pk_terapeuta']).update(
                fk_supervisor_id=sup_pk)
            supervisores_pk.add(sup_pk)
        for sup in Terapeuta.objects.filter(pk_terapeuta__in=supervisores_pk):
            sup.tags.add(tag_sup)

    def _migrar_m2m_tags(self, leg):
        for tabela, campo in (('terapeutas_tags', 'tags'),
                              ('terapeutas_tags_apto', 'tags_apto')):
            leg.execute(
                f"SELECT terapeuta_id, tag_id FROM {tabela} "
                f"WHERE terapeuta_id IN {_in(self.terapeuta_pks)}"
            )
            rows = _dictfetchall(leg)
            self._n(f"Vínculos {tabela} (recorte)", len(rows))
            if self.dry:
                continue
            porter = {}
            for r in rows:
                porter.setdefault(r['terapeuta_id'], []).append(r['tag_id'])
            for ter_pk, tag_ids in porter.items():
                ter = Terapeuta.objects.filter(pk_terapeuta=ter_pk).first()
                if ter:
                    getattr(ter, campo).add(*tag_ids)

    def _migrar_horarios(self, leg):
        leg.execute(
            "SELECT id, fk_terapeuta_id, dia_semana, hora_inicio, hora_fim "
            f"FROM principais_horariodisponivel WHERE fk_terapeuta_id IN {_in(self.terapeuta_pks)}"
        )
        rows = _dictfetchall(leg)
        self._n("Horários lidos (recorte)", len(rows))
        if self.dry:
            return
        for r in rows:
            HorarioDisponivel.objects.update_or_create(
                id=r['id'],
                defaults=dict(
                    fk_terapeuta_id=r['fk_terapeuta_id'], dia_semana=r['dia_semana'],
                    hora_inicio=r['hora_inicio'], hora_fim=r['hora_fim'],
                ),
            )

    def _migrar_pacientes(self, leg):
        leg.execute("SELECT pk_captacao, nome FROM captacoes")
        captacao_nome = {r['pk_captacao']: r['nome'] for r in _dictfetchall(leg)}

        # Só os pacientes dos terapeutas do recorte (todos os status).
        leg.execute(
            "SELECT pk_paciente, fk_terapeuta, fk_captacao, nome, email, telefone, "
            "contato_apoio, dat_nascimento, vlr_sessao, observacao, status_atendimento, "
            "origem_paciente, dia_semana_padrao, hora_padrao, "
            "cpf, cep, endereco, numero, complemento, bairro, cidade, uf "
            f"FROM pacientes WHERE fk_terapeuta IN {_in(self.terapeuta_pks)}"
        )
        rows = _dictfetchall(leg)
        self._n("Pacientes lidos (recorte)", len(rows))
        # Quebra por status para transparência no dry-run.
        por_status = {}
        for r in rows:
            por_status[r['status_atendimento']] = por_status.get(r['status_atendimento'], 0) + 1
        for st, n in sorted(por_status.items()):
            self.stdout.write(f"      {st}: {n}")
        if self.dry:
            return
        from principais.models import SessaoSemanal
        for r in rows:
            # ATIVO/AGUARDANDO → ativo; PAUSADO/outros → inativo (decidido).
            is_active = r['status_atendimento'] in STATUS_ATIVO
            pac, _ = Paciente.objects.update_or_create(
                pk_paciente=r['pk_paciente'],
                defaults=dict(
                    fk_terapeuta_id=r['fk_terapeuta'], nome=r['nome'], email=r['email'],
                    telefone=r['telefone'], contato_apoio=r['contato_apoio'],
                    dat_nascimento=r['dat_nascimento'], vlr_sessao=r['vlr_sessao'],
                    origem=captacao_nome.get(r['fk_captacao']),
                    is_active=is_active, observacao=r['observacao'],
                    origem_paciente=r['origem_paciente'],
                    cpf=r['cpf'] or None, cep=r['cep'], endereco=r['endereco'],
                    numero=r['numero'], complemento=r['complemento'], bairro=r['bairro'],
                    cidade=r['cidade'], uf=r['uf'],
                ),
            )
            if r['dia_semana_padrao'] is not None and r['hora_padrao'] is not None:
                SessaoSemanal.objects.get_or_create(
                    fk_paciente=pac, dia_semana=r['dia_semana_padrao'],
                    hora_inicio=r['hora_padrao'],
                )
