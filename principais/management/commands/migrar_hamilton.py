"""
Migração de corte único do Hamilton antigo → Hamilton 2.0 (D6, decisões #8/#20).

Lê o banco de PRODUÇÃO do Hamilton antigo por uma conexão de somente leitura
(`DATABASES['legado']`, ligada por `LEGADO_DATABASE_URL`) e recria no banco do 2.0:

  - Users (preservando o HASH de senha — copia o campo cru, sem `set_password`);
  - Associados (vínculo 1-1 com User);
  - Abordagens e Tags (garante as tags `supervisor` e `prefeitura`);
  - Terapeutas, mapeando o antigo `fk_decano` (um Associado) para o novo
    `fk_supervisor` (um Terapeuta) e marcando o supervisor com a tag `supervisor`;
  - M2M de tags (atuais / apto a);
  - HorárioDisponível;
  - Pacientes, com os campos fiscais e a captação antiga virando o campo `origem`.

Os IDs (`pk_*`) são preservados, então os vínculos User↔Associado↔Terapeuta e as
FKs continuam válidos.

Uso:
    python manage.py migrar_hamilton            # DRY-RUN (padrão): não grava nada
    python manage.py migrar_hamilton --executar # grava de verdade (go-live)

Momento (decisão #20): construído agora, executado só no go-live contra produção.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction
from django.contrib.auth.models import User

from principais.models import (
    Abordagem, Associado, HorarioDisponivel, Paciente, Tag, Terapeuta,
)


def _dictfetchall(cursor):
    cols = [c[0] for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


class Command(BaseCommand):
    help = "Migra dados do Hamilton antigo (banco legado) para o Hamilton 2.0."

    def add_arguments(self, parser):
        parser.add_argument(
            '--executar', action='store_true',
            help="Grava de verdade. Sem esta flag, roda em dry-run (não grava).",
        )

    def handle(self, *args, **opts):
        self.dry = not opts['executar']
        if 'legado' not in connections.databases:
            raise CommandError(
                "Conexão 'legado' não configurada. Defina LEGADO_DATABASE_URL no "
                "ambiente apontando para o banco de produção do Hamilton antigo "
                "(ver ../hamilton-api/.env). Só então a migração roda."
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
            "Dry-run concluído (nada gravado)." if self.dry
            else "Migração concluída."
        ))

    # ------------------------------------------------------------------ passos
    def _migrar(self, leg):
        self._migrar_users(leg)
        self._migrar_associados(leg)
        self._migrar_abordagens(leg)
        self._migrar_tags(leg)
        self._migrar_terapeutas(leg)          # 1º passo: sem supervisor
        self._migrar_supervisores(leg)        # 2º passo: fk_decano → fk_supervisor
        self._migrar_m2m_tags(leg)
        self._migrar_horarios(leg)
        self._migrar_pacientes(leg)

    def _n(self, rotulo, qtd):
        self.stdout.write(f"  {rotulo}: {qtd}")

    def _migrar_users(self, leg):
        leg.execute(
            "SELECT id, password, last_login, is_superuser, username, first_name, "
            "last_name, email, is_staff, is_active, date_joined FROM auth_user"
        )
        rows = _dictfetchall(leg)
        self._n("Users lidos", len(rows))
        if self.dry:
            return
        for r in rows:
            # password é o HASH cru — atribuído direto, nunca via set_password.
            User.objects.update_or_create(
                id=r['id'],
                defaults=dict(
                    password=r['password'], last_login=r['last_login'],
                    is_superuser=r['is_superuser'], username=r['username'],
                    first_name=r['first_name'] or '', last_name=r['last_name'] or '',
                    email=r['email'] or '', is_staff=r['is_staff'],
                    is_active=r['is_active'], date_joined=r['date_joined'],
                ),
            )

    def _migrar_associados(self, leg):
        leg.execute(
            "SELECT pk_associado, nome, email, telefone, contato_apoio, "
            "dat_nascimento, sexo, cpf, endereco, is_active, observacao, usuario_id "
            "FROM associados"
        )
        rows = _dictfetchall(leg)
        self._n("Associados lidos", len(rows))
        if self.dry:
            return
        for r in rows:
            Associado.objects.update_or_create(
                pk_associado=r['pk_associado'],
                defaults=dict(
                    nome=r['nome'], email=r['email'], telefone=r['telefone'],
                    contato_apoio=r['contato_apoio'], dat_nascimento=r['dat_nascimento'],
                    sexo=r['sexo'], cpf=r['cpf'], endereco=r['endereco'],
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
                pk_abordagem=r['pk_abordagem'],
                defaults=dict(abordagem=r['abordagem']),
            )

    def _migrar_tags(self, leg):
        leg.execute("SELECT pk_tag, nome FROM tags")
        rows = _dictfetchall(leg)
        self._n("Tags lidas", len(rows))
        if self.dry:
            # Garante que as tags-chave existem mesmo em dry-run? Não: dry não grava.
            return
        for r in rows:
            Tag.objects.update_or_create(
                pk_tag=r['pk_tag'], defaults=dict(nome=r['nome']),
            )
        # Tags-chave do 2.0 (decisões #5/#7) — criadas se não vieram do legado.
        for nome in ('supervisor', 'prefeitura'):
            Tag.objects.get_or_create(nome=nome)

    def _migrar_terapeutas(self, leg):
        leg.execute(
            "SELECT pk_terapeuta, fk_associado, fk_abordagem, pacientes_max, "
            "is_active, observacao, link_agenda FROM terapeutas"
        )
        rows = _dictfetchall(leg)
        self._n("Terapeutas lidos", len(rows))
        if self.dry:
            return
        for r in rows:
            Terapeuta.objects.update_or_create(
                pk_terapeuta=r['pk_terapeuta'],
                defaults=dict(
                    fk_associado_id=r['fk_associado'],
                    fk_abordagem_id=r['fk_abordagem'],
                    pacientes_max=r['pacientes_max'], is_active=r['is_active'],
                    observacao=r['observacao'], link_agenda=r['link_agenda'],
                    fk_supervisor=None,  # resolvido no 2º passo
                ),
            )

    def _migrar_supervisores(self, leg):
        """Mapeia o antigo `fk_decano` (Associado) para `fk_supervisor` (Terapeuta)
        e marca cada supervisor com a tag `supervisor` (decisão #7)."""
        leg.execute(
            "SELECT pk_terapeuta, fk_decano FROM terapeutas WHERE fk_decano IS NOT NULL"
        )
        rows = _dictfetchall(leg)
        # decano é um Associado; o supervisor no 2.0 é o Terapeuta daquele associado.
        assoc_para_terapeuta = {
            t.fk_associado_id: t.pk_terapeuta for t in Terapeuta.objects.all()
        } if not self.dry else {}
        sem_terapeuta = sum(
            1 for r in rows if r['fk_decano'] not in assoc_para_terapeuta
        ) if not self.dry else 0
        self._n("Terapeutas com decano", len(rows))
        if sem_terapeuta:
            self.stdout.write(self.style.WARNING(
                f"  (aviso) {sem_terapeuta} decano(s) sem Terapeuta correspondente — "
                f"ficam sem supervisor."
            ))
        if self.dry:
            return
        tag_sup, _ = Tag.objects.get_or_create(nome='supervisor')
        supervisores_pk = set()
        for r in rows:
            sup_pk = assoc_para_terapeuta.get(r['fk_decano'])
            if not sup_pk:
                continue
            Terapeuta.objects.filter(pk_terapeuta=r['pk_terapeuta']).update(
                fk_supervisor_id=sup_pk
            )
            supervisores_pk.add(sup_pk)
        for sup in Terapeuta.objects.filter(pk_terapeuta__in=supervisores_pk):
            sup.tags.add(tag_sup)

    def _migrar_m2m_tags(self, leg):
        for tabela, campo in (('terapeutas_tags', 'tags'),
                              ('terapeutas_tags_apto', 'tags_apto')):
            leg.execute(f"SELECT terapeuta_id, tag_id FROM {tabela}")
            rows = _dictfetchall(leg)
            self._n(f"Vínculos {tabela}", len(rows))
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
            "FROM principais_horariodisponivel"
        )
        rows = _dictfetchall(leg)
        self._n("Horários lidos", len(rows))
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
        # Captação antiga (texto) → campo `origem` do 2.0.
        leg.execute("SELECT pk_captacao, nome FROM captacoes")
        captacao_nome = {r['pk_captacao']: r['nome'] for r in _dictfetchall(leg)}

        # O 2.0 não tem mais status_atendimento (só is_active). Trazemos o
        # is_active do Hamilton antigo como fonte da situação.
        leg.execute(
            "SELECT pk_paciente, fk_terapeuta, fk_captacao, nome, email, telefone, "
            "contato_apoio, dat_nascimento, vlr_sessao, is_active, observacao, "
            "origem_paciente, dia_semana_padrao, hora_padrao, "
            "cpf, cep, endereco, numero, complemento, bairro, cidade, uf "
            "FROM pacientes"
        )
        rows = _dictfetchall(leg)
        self._n("Pacientes lidos", len(rows))
        if self.dry:
            return
        for r in rows:
            Paciente.objects.update_or_create(
                pk_paciente=r['pk_paciente'],
                defaults=dict(
                    fk_terapeuta_id=r['fk_terapeuta'], nome=r['nome'], email=r['email'],
                    telefone=r['telefone'], contato_apoio=r['contato_apoio'],
                    dat_nascimento=r['dat_nascimento'], vlr_sessao=r['vlr_sessao'],
                    origem=captacao_nome.get(r['fk_captacao']),
                    is_active=r['is_active'], observacao=r['observacao'],
                    origem_paciente=r['origem_paciente'],
                    dia_semana_padrao=r['dia_semana_padrao'], hora_padrao=r['hora_padrao'],
                    cpf=r['cpf'], cep=r['cep'], endereco=r['endereco'], numero=r['numero'],
                    complemento=r['complemento'], bairro=r['bairro'], cidade=r['cidade'],
                    uf=r['uf'],
                ),
            )
