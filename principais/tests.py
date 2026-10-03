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
    Abordagem, Associado, HorarioDisponivel, Notificacao, Paciente,
    SessaoSemanal, Tag, Terapeuta,
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
