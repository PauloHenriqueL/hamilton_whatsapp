"""Testes dos requisitos de horários/capacidade (grilling de 2026-10-03).

Cobrem: capacidade por horas contando SESSÕES (ex.: 7/15), multi-sessão por
paciente, tag como atividade no calendário, trava de pacientes_max na alocação
e trava de horas ao adicionar sessão, painel de substitutos, simplificação do
paciente (só is_active) e o aviso de desvio das 15h.
"""
import json
from datetime import time
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from principais.models import (
    Abordagem, Associado, HorarioDisponivel, Notificacao, PagadorAlternativo,
    Paciente, SessaoSemanal, Tag, Terapeuta,
)


def cria_terapeuta(nome, username=None, pacientes_max=15, supervisor=None):
    user = User.objects.create_user(username=username, password="x") if username else None
    assoc = Associado.objects.create(nome=nome, telefone="31988550000", usuario=user)
    return Terapeuta.objects.create(
        fk_associado=assoc, pacientes_max=pacientes_max, fk_supervisor=supervisor)


def bloco(ter, dia, ini, fim, tag=None):
    return HorarioDisponivel.objects.create(
        fk_terapeuta=ter, dia_semana=dia, hora_inicio=ini, hora_fim=fim, fk_tag=tag)


def paciente(nome, ter=None, ativo=True, sessoes=None):
    p = Paciente.objects.create(
        nome=nome, telefone="31977770000", vlr_sessao=Decimal("200"),
        fk_terapeuta=ter, is_active=ativo)
    for dia, hora in (sessoes or []):
        SessaoSemanal.objects.create(fk_paciente=p, dia_semana=dia, hora_inicio=hora)
    return p


class CapacidadePorHorasTest(TestCase):
    def test_horas_total_soma_todos_os_blocos(self):
        t = cria_terapeuta("T1")
        bloco(t, 0, time(8, 0), time(12, 0))   # 4h
        bloco(t, 2, time(14, 0), time(17, 0))  # 3h
        self.assertEqual(t.horas_total, Decimal("7"))

    def test_tag_block_conta_como_ocupado(self):
        t = cria_terapeuta("T2")
        grupo = Tag.objects.create(nome="Grupo", horas_consumidas=Decimal("3"))
        bloco(t, 0, time(8, 0), time(11, 0), tag=grupo)  # 3h atividade
        bloco(t, 0, time(11, 0), time(12, 0))            # 1h livre
        self.assertEqual(t.horas_tags, Decimal("3"))
        self.assertEqual(t.horas_ocupadas, Decimal("3"))   # sem sessões
        self.assertEqual(t.horas_livres, Decimal("1"))

    def test_exemplo_do_cliente_sete_de_quinze(self):
        """15h (12h livre + 3h atividade) + 4 sessões = 7/15."""
        t = cria_terapeuta("Ana")
        grupo = Tag.objects.create(nome="Grupo de estudos", horas_consumidas=Decimal("3"))
        bloco(t, 0, time(8, 0), time(11, 0), tag=grupo)  # 3h
        bloco(t, 2, time(8, 0), time(14, 0))             # 6h
        bloco(t, 4, time(8, 0), time(14, 0))             # 6h -> total 15h
        paciente("P1", ter=t, sessoes=[(2, time(8, 0)), (2, time(9, 0))])  # 2 sessões
        paciente("P2", ter=t, sessoes=[(2, time(10, 0))])
        paciente("P3", ter=t, sessoes=[(2, time(11, 0))])
        self.assertEqual(t.horas_total, Decimal("15"))
        self.assertEqual(t.sessoes_count, 4)
        self.assertEqual(t.horas_ocupadas, Decimal("7"))   # 3 (tag) + 4 (sessões)
        self.assertEqual(t.horas_livres, Decimal("8"))

    def test_multi_sessao_mesmo_paciente_conta_duas_horas(self):
        t = cria_terapeuta("T")
        bloco(t, 0, time(8, 0), time(18, 0))  # 10h
        paciente("Mariana", ter=t, sessoes=[(0, time(8, 0)), (3, time(9, 0))])
        self.assertEqual(t.sessoes_count, 2)
        self.assertEqual(t.horas_ocupadas, Decimal("2"))  # 1 paciente, 2 sessões

    def test_paciente_inativo_nao_conta(self):
        t = cria_terapeuta("T")
        bloco(t, 0, time(8, 0), time(13, 0))
        paciente("Ativo", ter=t, sessoes=[(0, time(8, 0))])
        paciente("Inativo", ter=t, ativo=False, sessoes=[(0, time(9, 0))])
        self.assertEqual(t.horas_ocupadas, Decimal("1"))

    def test_desvio_das_quinze(self):
        t = cria_terapeuta("T")
        bloco(t, 0, time(8, 0), time(18, 0))  # 10h
        self.assertTrue(t.horas_fora_da_recomendacao)


class AlocacaoTest(TestCase):
    def setUp(self):
        self.gestor = User.objects.create_user("gestor", password="x", is_staff=True)
        self.client.force_login(self.gestor)

    def _alocar(self, pac, ter):
        return self.client.post("/encaminhamento/alocar/", {
            "paciente_id": pac.pk_paciente, "terapeuta_id": ter.pk_terapeuta}, follow=True)

    def test_vincular_bloqueia_por_pacientes_max(self):
        t = cria_terapeuta("T", pacientes_max=1)
        bloco(t, 0, time(8, 0), time(18, 0))
        paciente("Já", ter=t)
        novo = paciente("Novo", ter=None)
        self._alocar(novo, t)
        novo.refresh_from_db()
        self.assertIsNone(novo.fk_terapeuta_id)

    def test_vincular_nao_bloqueia_por_horas(self):
        """Vincular paciente não consome hora; a trava de horas é na sessão."""
        t = cria_terapeuta("T", pacientes_max=10)
        bloco(t, 0, time(8, 0), time(9, 0))  # 1h só
        paciente("Já", ter=t, sessoes=[(0, time(8, 0))])  # ocupa a única hora
        novo = paciente("Novo", ter=None)
        self._alocar(novo, t)
        novo.refresh_from_db()
        self.assertEqual(novo.fk_terapeuta_id, t.pk_terapeuta)  # vincula mesmo sem hora


class SessaoAPITest(TestCase):
    def setUp(self):
        self.ter = cria_terapeuta("Ana", username="ana", pacientes_max=10)
        bloco(self.ter, 0, time(8, 0), time(12, 0))  # 4h disponível
        self.pac = paciente("Mariana", ter=self.ter)
        self.aloc_url = f"/terapeutas/{self.ter.pk_terapeuta}/alocar-paciente-horario/"

    def _add(self, dia, inicio, pid=None):
        return self.client.post(self.aloc_url, data=json.dumps(
            {"paciente_id": pid or self.pac.pk_paciente, "dia": dia, "inicio": inicio}),
            content_type="application/json")

    def test_terapeuta_adiciona_varias_sessoes(self):
        self.client.force_login(self.ter.fk_associado.usuario)
        self.assertEqual(self._add(0, "08:00").status_code, 200)
        self.assertEqual(self._add(0, "09:00").status_code, 200)
        self.assertEqual(self.pac.sessoes.count(), 2)

    def test_sessao_duplicada_rejeitada(self):
        self.client.force_login(self.ter.fk_associado.usuario)
        self._add(0, "08:00")
        r = self._add(0, "08:00")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.pac.sessoes.count(), 1)

    def test_sem_horas_livres_rejeita_sessao(self):
        # 4h disponível, preenche com 4 sessões -> 5a sem hora livre.
        self.client.force_login(self.ter.fk_associado.usuario)
        for h in ("08:00", "09:00", "10:00", "11:00"):
            self.assertEqual(self._add(0, h).status_code, 200)
        r = self._add(1, "08:00")
        self.assertEqual(r.status_code, 400)

    def test_remover_sessao(self):
        self.client.force_login(self.ter.fk_associado.usuario)
        self._add(0, "08:00")
        s = self.pac.sessoes.first()
        r = self.client.post(f"/sessoes/{s.pk}/remover/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.pac.sessoes.count(), 0)

    def test_outro_terapeuta_nao_aloca(self):
        intruso = cria_terapeuta("Intruso", username="intruso")
        self.client.force_login(intruso.fk_associado.usuario)
        self.assertEqual(self._add(0, "08:00").status_code, 403)

    def test_sessao_meia_hora_bloqueia_hora_seguinte(self):
        """Bug relatado: 08:30 (até 09:30) deve bloquear uma sessão às 09:00."""
        self.client.force_login(self.ter.fk_associado.usuario)
        outro = paciente("Outro", ter=self.ter)
        self.assertEqual(self._add(0, "08:30").status_code, 200)
        r = self._add(0, "09:00", pid=outro.pk_paciente)   # sobrepõe 08:30–09:30
        self.assertEqual(r.status_code, 400)
        self.assertIn("Conflito", r.json()["detail"])

    def test_sessao_anterior_sobreposta_tambem_bloqueia(self):
        """09:00 já existe; 08:30 (até 09:30) sobrepõe e deve bloquear."""
        self.client.force_login(self.ter.fk_associado.usuario)
        outro = paciente("Outro", ter=self.ter)
        self.assertEqual(self._add(0, "09:00").status_code, 200)
        r = self._add(0, "08:30", pid=outro.pk_paciente)
        self.assertEqual(r.status_code, 400)

    def test_sessoes_encostadas_nao_conflitam(self):
        """08:30–09:30 e 09:30–10:30 só se encostam, não sobrepõem: ambas ok."""
        self.client.force_login(self.ter.fk_associado.usuario)
        outro = paciente("Outro", ter=self.ter)
        self.assertEqual(self._add(0, "08:30").status_code, 200)
        self.assertEqual(self._add(0, "09:30", pid=outro.pk_paciente).status_code, 200)

    def test_sessao_sobrepoe_bloco_de_atividade(self):
        """Bloco de atividade (tag) 10:00–11:00 bloqueia sessão às 10:30."""
        self.client.force_login(self.ter.fk_associado.usuario)
        grupo = Tag.objects.create(nome="Grupo")
        self.ter.tags.add(grupo)
        bloco(self.ter, 0, time(10, 0), time(11, 0), tag=grupo)
        r = self._add(0, "10:30")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Conflito", r.json()["detail"])


class SalvarHorariosAPITest(TestCase):
    def setUp(self):
        self.ter = cria_terapeuta("Ana", username="ana")
        self.grupo = Tag.objects.create(nome="Grupo", horas_consumidas=Decimal("2"))
        self.ter.tags.add(self.grupo)
        self.url = f"/terapeutas/{self.ter.pk_terapeuta}/horarios/salvar/"

    def _post(self, blocos):
        return self.client.post(self.url, data=json.dumps({"blocos": blocos}),
                                content_type="application/json")

    def test_rejeita_sobreposicao(self):
        self.client.force_login(self.ter.fk_associado.usuario)
        r = self._post([
            {"dia": 1, "inicio": "08:00", "fim": "10:00", "tag_id": None},
            {"dia": 1, "inicio": "09:00", "fim": "11:00", "tag_id": None}])
        self.assertEqual(r.status_code, 400)

    def test_desvio_gera_uma_notificacao_e_dedupe(self):
        self.client.force_login(self.ter.fk_associado.usuario)
        with patch("principais.whatsapp.enviar_whatsapp"):
            self._post([{"dia": 0, "inicio": "08:00", "fim": "10:00", "tag_id": None}])  # 2h
            self._post([{"dia": 0, "inicio": "08:00", "fim": "10:00", "tag_id": None}])  # de novo
        self.assertEqual(
            Notificacao.objects.filter(destinatario=self.ter.fk_associado).count(), 1)


class PainelSubstitutosTest(TestCase):
    def test_quem_da_e_quem_apto(self):
        grupo = Tag.objects.create(nome="Grupo de estudos", horas_consumidas=Decimal("3"))
        da = cria_terapeuta("Quem da")
        da.tags.add(grupo)
        bloco(da, 2, time(14, 0), time(17, 0), tag=grupo)
        apto = cria_terapeuta("Quem e apto")
        apto.tags_apto.add(grupo)
        from principais.views_controle_terapeutas import _painel_substitutos
        ativ = next(a for a in _painel_substitutos() if a["nome"] == "Grupo de estudos")
        self.assertEqual(ativ["quem_da"][0]["terapeuta"], "Quem da")
        nomes = [p["terapeuta"] for p in ativ["quem_apto"]]
        self.assertIn("Quem e apto", nomes)
        self.assertNotIn("Quem da", nomes)


class PacienteSituacaoTest(TestCase):
    def test_sem_status_atendimento(self):
        campos = [f.name for f in Paciente._meta.get_fields()]
        self.assertNotIn("status_atendimento", campos)
        self.assertNotIn("dia_semana_padrao", campos)

    def test_aguardando_e_ativo_sem_terapeuta(self):
        p = paciente("Aguardando", ter=None, ativo=True)
        self.assertIn(p, Paciente.objects.filter(is_active=True, fk_terapeuta__isnull=True))


class PacienteFormPagadoresTest(TestCase):
    """O cadastro de paciente salva os pagadores alternativos (inline formset)."""
    def setUp(self):
        self.gestor = User.objects.create_user("gestor", password="x", is_staff=True)
        self.client.force_login(self.gestor)

    def _payload(self, **extra):
        base = {
            "nome": "Paulo Lima", "telefone": "31988550000",
            "vlr_sessao": "200", "origem_paciente": "NOVO", "is_active": "on",
            # management form do formset de pagadores
            "pagadores-TOTAL_FORMS": "2", "pagadores-INITIAL_FORMS": "0",
            "pagadores-MIN_NUM_FORMS": "0", "pagadores-MAX_NUM_FORMS": "1000",
            "pagadores-0-nome": "Maria Aparecida",
            "pagadores-1-nome": "Rodolpho Lima",
        }
        base.update(extra)
        return base

    def test_cria_paciente_com_pagadores(self):
        r = self.client.post("/pacientes/novo/", self._payload())
        self.assertEqual(r.status_code, 302)
        p = Paciente.objects.get(nome="Paulo Lima")
        self.assertEqual(
            set(p.pagadores.values_list("nome", flat=True)),
            {"Maria Aparecida", "Rodolpho Lima"})

    def test_linha_vazia_e_ignorada(self):
        r = self.client.post("/pacientes/novo/", self._payload(**{
            "pagadores-1-nome": ""}))  # segunda linha vazia
        self.assertEqual(r.status_code, 302)
        p = Paciente.objects.get(nome="Paulo Lima")
        self.assertEqual(p.pagadores.count(), 1)


class DataPagamentoTest(TestCase):
    def test_dia_esperado_derivado_da_data(self):
        from datetime import date
        p = paciente("P", ter=None)
        p.data_primeiro_pagamento = date(2026, 9, 10)
        self.assertEqual(p.dia_pagamento_esperado, 10)

    def test_sem_data_dia_esperado_none(self):
        self.assertIsNone(paciente("P").dia_pagamento_esperado)

    def test_form_salva_data_primeiro_pagamento(self):
        gestor = User.objects.create_user("g2", password="x", is_staff=True)
        self.client.force_login(gestor)
        r = self.client.post("/pacientes/novo/", {
            "nome": "Paulo", "telefone": "31988550000", "vlr_sessao": "200",
            "origem_paciente": "NOVO", "is_active": "on",
            "data_primeiro_pagamento": "2026-09-10",
            "pagadores-TOTAL_FORMS": "0", "pagadores-INITIAL_FORMS": "0",
            "pagadores-MIN_NUM_FORMS": "0", "pagadores-MAX_NUM_FORMS": "1000",
        })
        self.assertEqual(r.status_code, 302)
        from datetime import date
        self.assertEqual(
            Paciente.objects.get(nome="Paulo").data_primeiro_pagamento, date(2026, 9, 10))


class WhatsAppClientTest(TestCase):
    def test_normalizar_telefone(self):
        from principais.whatsapp import normalizar_telefone as n
        self.assertEqual(n("31988550000"), "5531988550000")
        self.assertEqual(n("(31) 98855-0000"), "5531988550000")
        self.assertEqual(n("5531988550000"), "5531988550000")
        self.assertIsNone(n("123"))

    def test_dry_run_nao_envia_mas_retorna_true(self):
        from principais import whatsapp
        with patch.dict("os.environ", {"WHATSAPP_DRY_RUN": "true"}), \
                patch("principais.whatsapp.requests.post") as post:
            self.assertTrue(whatsapp.enviar_whatsapp("31988550000", "oi"))
            post.assert_not_called()


class LembreteSessaoTest(TestCase):
    def test_lembra_paciente_e_terapeuta(self):
        t = cria_terapeuta("Ana")
        p = paciente("Mariana", ter=t, sessoes=[(2, time(14, 0))])
        s = p.sessoes.first()
        with patch("principais.whatsapp_mensagens.enviar_template") as tpl:
            n = __import__("principais.whatsapp_mensagens", fromlist=["lembrar_sessao"]).lembrar_sessao(s)
        self.assertEqual(n, 2)                     # paciente + terapeuta
        self.assertEqual(tpl.call_count, 2)
        self.assertEqual(Notificacao.objects.filter(
            destinatario=t.fk_associado).count(), 1)  # in-system do terapeuta


class CobrancaEscalonamentoTest(TestCase):
    def setUp(self):
        gestor_user = User.objects.create_user("gestor", password="x", is_staff=True)
        self.gestor_assoc = Associado.objects.create(
            nome="Gestor", telefone="31900000000", usuario=gestor_user)
        self.sup = cria_terapeuta("Super")
        self.ter = cria_terapeuta("Ter", supervisor=self.sup)
        self.pac = paciente("Atrasado", ter=self.ter)

    def _cobrar(self, meses):
        from principais.whatsapp_mensagens import cobrar_atraso
        with patch("principais.whatsapp_mensagens.enviar_template"):
            return cobrar_atraso(self.pac, meses)

    def test_um_mes_so_terapeuta(self):
        self.assertEqual(self._cobrar(1), 1)

    def test_dois_meses_inclui_supervisor(self):
        self.assertEqual(self._cobrar(2), 2)

    def test_tres_meses_inclui_gestor(self):
        self.assertEqual(self._cobrar(3), 3)  # terapeuta + supervisor + gestor


class AtrasoDeteccaoTest(TestCase):
    def _trans(self, pac, ano, mes, dia=15):
        from conciliacao.models import ExtratoOFX, TransacaoOFX
        from datetime import date as d
        ext, _ = ExtratoOFX.objects.get_or_create(
            hash_arquivo=f"h{ano}{mes}", defaults={"arquivo_nome": "x.ofx"})
        return TransacaoOFX.objects.create(
            fk_extrato=ext, fitid=f"{pac.pk}-{ano}-{mes}", data=d(ano, mes, dia),
            valor=Decimal("200"), nome_pagador=pac.nome, fk_paciente=pac,
            status_conciliacao=TransacaoOFX.CONCILIADO)

    def test_sem_dados_de_ofx_nao_acusa_atraso(self):
        from principais.management.commands.cobrar_atrasos import Command
        t = cria_terapeuta("T")
        p = paciente("P", ter=t)
        self.assertEqual(Command()._meses_em_aberto(p, 2026, 9), 0)

    def test_nao_pagou_dois_meses_com_dados(self):
        from principais.management.commands.cobrar_atrasos import Command
        t = cria_terapeuta("T")
        p = paciente("P", ter=t)
        outro = paciente("Outro", ter=t)
        # Há OFX em ago e set (outro paciente pagou), mas P não pagou nenhum.
        self._trans(outro, 2026, 8)
        self._trans(outro, 2026, 9)
        self.assertEqual(Command()._meses_em_aberto(p, 2026, 9), 2)

    def test_pagou_o_mes_encerra_atraso(self):
        from principais.management.commands.cobrar_atrasos import Command
        t = cria_terapeuta("T")
        p = paciente("P", ter=t)
        self._trans(p, 2026, 9)  # pagou setembro
        self.assertEqual(Command()._meses_em_aberto(p, 2026, 9), 0)
