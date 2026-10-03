"""Testes dos requisitos de horários/capacidade (grilling de 2026-10-03).

Cobrem: capacidade por horas (ex.: 7/15), tag como atividade no calendário,
trava dupla na alocação (pacientes_max E horas), painel de substitutos,
simplificação do paciente (só is_active) e o aviso de desvio das 15h.
"""
import json
from datetime import time
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from principais.models import (
    Abordagem, Associado, HorarioDisponivel, Notificacao, Paciente, Tag, Terapeuta,
)


def cria_terapeuta(nome, username=None, pacientes_max=15, supervisor=None):
    user = None
    if username:
        user = User.objects.create_user(username=username, password="x")
    assoc = Associado.objects.create(nome=nome, telefone="31988550000", usuario=user)
    return Terapeuta.objects.create(
        fk_associado=assoc, pacientes_max=pacientes_max, fk_supervisor=supervisor,
    )


def bloco(ter, dia, ini, fim, tag=None):
    return HorarioDisponivel.objects.create(
        fk_terapeuta=ter, dia_semana=dia, hora_inicio=ini, hora_fim=fim, fk_tag=tag,
    )


def paciente(nome, ter=None, ativo=True, dia=None, hora=None):
    return Paciente.objects.create(
        nome=nome, telefone="31977770000", vlr_sessao=Decimal("200"),
        fk_terapeuta=ter, is_active=ativo, dia_semana_padrao=dia, hora_padrao=hora,
    )


class CapacidadePorHorasTest(TestCase):
    """O denominador é a soma real dos blocos; ocupado = pacientes (1h) + tags."""

    def test_horas_total_soma_todos_os_blocos(self):
        t = cria_terapeuta("T1")
        bloco(t, 0, time(8, 0), time(12, 0))   # 4h
        bloco(t, 2, time(14, 0), time(17, 0))  # 3h
        self.assertEqual(t.horas_total, Decimal("7"))

    def test_tag_block_conta_como_ocupado_mas_nao_disponivel(self):
        t = cria_terapeuta("T2")
        grupo = Tag.objects.create(nome="Grupo", horas_consumidas=Decimal("3"))
        bloco(t, 0, time(8, 0), time(11, 0), tag=grupo)  # 3h de atividade
        bloco(t, 0, time(11, 0), time(12, 0))            # 1h livre
        self.assertEqual(t.horas_tags, Decimal("3"))
        self.assertEqual(t.horas_total, Decimal("4"))
        self.assertEqual(t.horas_ocupadas, Decimal("3"))   # só a tag, sem pacientes
        self.assertEqual(t.horas_livres, Decimal("1"))

    def test_exemplo_do_cliente_sete_de_quinze(self):
        """15h (12h livre + 3h de atividade) + 4 pacientes = 7/15."""
        t = cria_terapeuta("Ana")
        grupo = Tag.objects.create(nome="Grupo de estudos", horas_consumidas=Decimal("3"))
        bloco(t, 0, time(8, 0), time(11, 0), tag=grupo)  # 3h atividade
        bloco(t, 2, time(8, 0), time(14, 0))             # 6h livre
        bloco(t, 4, time(8, 0), time(14, 0))             # 6h livre  -> total 15h
        for i in range(4):
            paciente(f"P{i}", ter=t)
        self.assertEqual(t.horas_total, Decimal("15"))
        self.assertEqual(t.horas_ocupadas, Decimal("7"))   # 3 (tag) + 4 (pacientes)
        self.assertEqual(t.horas_livres, Decimal("8"))
        self.assertFalse(t.horas_fora_da_recomendacao)

    def test_paciente_inativo_nao_conta_hora(self):
        t = cria_terapeuta("T3")
        bloco(t, 0, time(8, 0), time(13, 0))  # 5h
        paciente("Ativo", ter=t, ativo=True)
        paciente("Inativo", ter=t, ativo=False)
        self.assertEqual(t.horas_ocupadas, Decimal("1"))  # só o ativo

    def test_desvio_das_quinze_horas(self):
        t = cria_terapeuta("T4")
        bloco(t, 0, time(8, 0), time(18, 0))  # 10h -> fora de 15
        self.assertTrue(t.horas_fora_da_recomendacao)


class TravaDuplaAlocacaoTest(TestCase):
    """Vale o limite que estourar primeiro: pacientes_max OU horas livres."""

    def setUp(self):
        self.gestor = User.objects.create_user(
            username="gestor", password="x", is_staff=True)
        self.client.force_login(self.gestor)

    def _alocar(self, pac, ter):
        return self.client.post("/encaminhamento/alocar/", {
            "paciente_id": pac.pk_paciente, "terapeuta_id": ter.pk_terapeuta,
        }, follow=True)

    def test_bloqueia_por_pacientes_max(self):
        t = cria_terapeuta("T", pacientes_max=1)
        bloco(t, 0, time(8, 0), time(18, 0))  # 10h livres, folga de horas
        paciente("Já", ter=t)                 # atinge o max=1
        novo = paciente("Novo", ter=None)
        self._alocar(novo, t)
        novo.refresh_from_db()
        self.assertIsNone(novo.fk_terapeuta_id)  # não alocou (max de pacientes)

    def test_bloqueia_por_horas_livres(self):
        t = cria_terapeuta("T", pacientes_max=99)
        bloco(t, 0, time(8, 0), time(9, 0))  # só 1h total
        paciente("Já", ter=t)                # ocupa a única hora -> 0 livres
        novo = paciente("Novo", ter=None)
        self._alocar(novo, t)
        novo.refresh_from_db()
        self.assertIsNone(novo.fk_terapeuta_id)  # não alocou (sem horas)

    def test_aloca_quando_ha_folga_nos_dois(self):
        t = cria_terapeuta("T", pacientes_max=10)
        bloco(t, 0, time(8, 0), time(18, 0))  # 10h livres
        novo = paciente("Novo", ter=None)
        self._alocar(novo, t)
        novo.refresh_from_db()
        self.assertEqual(novo.fk_terapeuta_id, t.pk_terapeuta)
        self.assertTrue(novo.is_active)


class SalvarHorariosAPITest(TestCase):
    def setUp(self):
        self.ter = cria_terapeuta("Ana", username="ana")
        self.grupo = Tag.objects.create(nome="Grupo", horas_consumidas=Decimal("2"))
        self.ter.tags.add(self.grupo)
        self.url = f"/terapeutas/{self.ter.pk_terapeuta}/horarios/salvar/"

    def _post(self, blocos):
        return self.client.post(
            self.url, data=json.dumps({"blocos": blocos}),
            content_type="application/json")

    def test_terapeuta_salva_proprio_calendario(self):
        self.client.force_login(self.ter.fk_associado.usuario)
        r = self._post([
            {"dia": 0, "inicio": "08:00", "fim": "10:00", "tag_id": self.grupo.pk_tag},
            {"dia": 0, "inicio": "10:00", "fim": "12:00", "tag_id": None},
        ])
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.ter.horarios.count(), 2)
        self.assertEqual(self.ter.horas_tags, Decimal("2"))

    def test_rejeita_sobreposicao(self):
        self.client.force_login(self.ter.fk_associado.usuario)
        r = self._post([
            {"dia": 1, "inicio": "08:00", "fim": "10:00", "tag_id": None},
            {"dia": 1, "inicio": "09:00", "fim": "11:00", "tag_id": None},
        ])
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.ter.horarios.count(), 0)

    def test_rejeita_tag_nao_atribuida(self):
        outra = Tag.objects.create(nome="Outra")
        self.client.force_login(self.ter.fk_associado.usuario)
        r = self._post([{"dia": 0, "inicio": "08:00", "fim": "09:00", "tag_id": outra.pk_tag}])
        self.assertEqual(r.status_code, 400)

    def test_outro_terapeuta_nao_pode_salvar(self):
        intruso = cria_terapeuta("Intruso", username="intruso")
        self.client.force_login(intruso.fk_associado.usuario)
        r = self._post([{"dia": 0, "inicio": "08:00", "fim": "09:00", "tag_id": None}])
        self.assertEqual(r.status_code, 403)

    def test_desvio_das_quinze_gera_notificacao_e_whatsapp(self):
        self.client.force_login(self.ter.fk_associado.usuario)
        with patch("principais.whatsapp.enviar_whatsapp") as mock_wpp:
            self._post([{"dia": 0, "inicio": "08:00", "fim": "10:00", "tag_id": None}])  # 2h != 15
        self.assertEqual(
            Notificacao.objects.filter(destinatario=self.ter.fk_associado).count(), 1)
        mock_wpp.assert_called_once()

    def test_total_igual_quinze_nao_gera_aviso(self):
        self.client.force_login(self.ter.fk_associado.usuario)
        with patch("principais.whatsapp.enviar_whatsapp") as mock_wpp:
            self._post([{"dia": 0, "inicio": "08:00", "fim": "14:00", "tag_id": None},   # 6h
                        {"dia": 2, "inicio": "08:00", "fim": "14:00", "tag_id": None},   # 6h
                        {"dia": 4, "inicio": "08:00", "fim": "11:00", "tag_id": None}])  # 3h = 15
        self.assertEqual(Notificacao.objects.count(), 0)
        mock_wpp.assert_not_called()


class PainelSubstitutosTest(TestCase):
    def setUp(self):
        self.gestor = User.objects.create_user(
            username="gestor", password="x", is_staff=True)
        self.client.force_login(self.gestor)

    def test_quem_da_e_quem_esta_apto(self):
        grupo = Tag.objects.create(nome="Grupo de estudos", horas_consumidas=Decimal("3"))
        da = cria_terapeuta("Quem da")
        da.tags.add(grupo)
        bloco(da, 2, time(14, 0), time(17, 0), tag=grupo)  # dá quarta 14-17
        apto = cria_terapeuta("Quem e apto")
        apto.tags_apto.add(grupo)

        from principais.views_controle_terapeutas import _painel_substitutos
        atividades = _painel_substitutos()
        ativ = next(a for a in atividades if a["nome"] == "Grupo de estudos")
        self.assertEqual(len(ativ["quem_da"]), 1)
        self.assertEqual(ativ["quem_da"][0]["terapeuta"], "Quem da")
        self.assertIn("Qua", ativ["quem_da"][0]["dia"])
        nomes_aptos = [p["terapeuta"] for p in ativ["quem_apto"]]
        self.assertIn("Quem e apto", nomes_aptos)
        self.assertNotIn("Quem da", nomes_aptos)  # quem já dá não aparece como apto


class PacienteSituacaoTest(TestCase):
    """Paciente só tem is_active; 'aguardando' = ativo sem terapeuta."""

    def test_sem_campo_status_atendimento(self):
        self.assertFalse(hasattr(Paciente, "STATUS_CHOICES"))
        campos = [f.name for f in Paciente._meta.get_fields()]
        self.assertNotIn("status_atendimento", campos)

    def test_aguardando_encaminhamento_e_ativo_sem_terapeuta(self):
        p = paciente("Aguardando", ter=None, ativo=True)
        aguardando = Paciente.objects.filter(is_active=True, fk_terapeuta__isnull=True)
        self.assertIn(p, aguardando)
