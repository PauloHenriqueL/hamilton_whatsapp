"""Testes do dashboard (D20) — os 2 KPIs (decisão #18) e o roteamento por papel.

KPI 1 = pacientes ativos × soma do pacientes_max dos terapeutas ATIVOS.
KPI 2 = créditos OFX não identificados em aberto.
Terapeuta (não-staff) é redirecionado para Meus Horários.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from principais.models import Associado, Paciente, Terapeuta

from conciliacao.models import ExtratoOFX, TransacaoOFX


def cria_terapeuta(nome, username=None, pacientes_max=10, ativo=True):
    user = User.objects.create_user(username=username, password="x") if username else None
    assoc = Associado.objects.create(nome=nome, telefone="31988550000", usuario=user)
    return Terapeuta.objects.create(
        fk_associado=assoc, pacientes_max=pacientes_max, is_active=ativo)


def paciente(nome, ter=None, ativo=True):
    return Paciente.objects.create(
        nome=nome, telefone="31977770000", vlr_sessao=Decimal("200"),
        fk_terapeuta=ter, is_active=ativo)


def nao_identificado(fitid):
    ext, _ = ExtratoOFX.objects.get_or_create(
        hash_arquivo="h", defaults={"arquivo_nome": "x.ofx"})
    return TransacaoOFX.objects.create(
        fk_extrato=ext, fitid=fitid, data=date(2026, 9, 10), valor=Decimal("200"),
        nome_pagador="Fantasma", status_conciliacao=TransacaoOFX.NAO_IDENTIFICADO)


class KPITest(TestCase):
    def setUp(self):
        self.gestor = User.objects.create_user("gestor", password="x", is_staff=True)
        self.client.force_login(self.gestor)

    def _ctx(self):
        return self.client.get("/").context

    def test_kpi_capacidade_soma_so_terapeutas_ativos(self):
        cria_terapeuta("Ativo A", pacientes_max=15)
        cria_terapeuta("Ativo B", pacientes_max=10)
        cria_terapeuta("Inativo", pacientes_max=20, ativo=False)
        ctx = self._ctx()
        self.assertEqual(ctx["kpi_capacidade_total"], 25)   # 15 + 10 (inativo fora)

    def test_kpi_pacientes_ativos_conta_so_ativos(self):
        paciente("P1")
        paciente("P2")
        paciente("Inativo", ativo=False)
        self.assertEqual(self._ctx()["kpi_pacientes_ativos"], 2)

    def test_kpi_pendencias_conta_so_nao_identificados(self):
        nao_identificado("a")
        nao_identificado("b")
        ext = ExtratoOFX.objects.first()
        TransacaoOFX.objects.create(
            fk_extrato=ext, fitid="c", data=date(2026, 9, 10), valor=Decimal("200"),
            nome_pagador="Ok", status_conciliacao=TransacaoOFX.CONCILIADO)
        self.assertEqual(self._ctx()["kpi_pendencias_conciliacao"], 2)

    def test_sem_dados_kpis_zerados(self):
        ctx = self._ctx()
        self.assertEqual(ctx["kpi_capacidade_total"], 0)
        self.assertEqual(ctx["kpi_pacientes_ativos"], 0)
        self.assertEqual(ctx["kpi_pendencias_conciliacao"], 0)


class RoteamentoPorPapelTest(TestCase):
    def test_gestor_ve_dashboard(self):
        self.client.force_login(User.objects.create_user("gestor", password="x", is_staff=True))
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, "dashboard.html")

    def test_terapeuta_redireciona_para_meus_horarios(self):
        ter = cria_terapeuta("Ana", username="ana")
        self.client.force_login(ter.fk_associado.usuario)
        r = self.client.get("/")
        self.assertRedirects(r, "/meus-horarios/", fetch_redirect_response=False)

    def test_anonimo_vai_para_login(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r["Location"])
