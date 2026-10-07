"""Testes das notas fiscais (D16–D19).

Cobrem o fechamento do mês (gera uma NotaFiscal por paciente pago a partir da
soma real do OFX — decisões #2/#3), as regras de isento (decisão #5) e sem CPF
(decisão #4), a idempotência (uma nota por paciente por mês), a montagem do
payload da NFS-e (texto de imunidade, valor zero → R$ 0,01, tomador) e a
emissão via Webmania com o cliente mockado (a assinatura real está inativa).
"""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase

from principais.models import Paciente

from conciliacao.models import ExtratoOFX, TransacaoOFX
from fiscal.config import TEXTO_IMUNIDADE
from fiscal.models import NotaFiscal
from fiscal.services import competencia_mes_anterior, gerar_notas_do_mes
from fiscal.views import _emitir_nota, _montar_nfs_info


def paciente(nome, valor="200", cpf="52998224725"):
    return Paciente.objects.create(
        nome=nome, telefone="31977770000", vlr_sessao=Decimal(valor),
        cpf=cpf, cep="30140071", endereco="R Teste", numero="10",
        bairro="Centro", cidade="Belo Horizonte", uf="MG", is_active=True)


def credito(pac, valor="200", quando=date(2026, 9, 10), fitid="f1"):
    ext, _ = ExtratoOFX.objects.get_or_create(
        hash_arquivo="h", defaults={"arquivo_nome": "x.ofx"})
    return TransacaoOFX.objects.create(
        fk_extrato=ext, fitid=fitid, data=quando, valor=Decimal(valor),
        nome_pagador=pac.nome, fk_paciente=pac,
        status_conciliacao=TransacaoOFX.CONCILIADO)


class CompetenciaTest(TestCase):
    def test_mes_anterior(self):
        self.assertEqual(competencia_mes_anterior(date(2026, 10, 15)), date(2026, 9, 1))
        self.assertEqual(competencia_mes_anterior(date(2026, 1, 3)), date(2025, 12, 1))


class GerarNotasDoMesTest(TestCase):
    COMP = date(2026, 9, 1)

    def test_cria_nota_pela_soma_real_do_ofx(self):
        p = paciente("Joao", valor="200")
        credito(p, "200", date(2026, 9, 5), fitid="a")
        credito(p, "200", date(2026, 9, 20), fitid="b")   # pagou 2x no mês
        res = gerar_notas_do_mes(self.COMP)
        self.assertEqual(res.criadas, 1)
        nota = NotaFiscal.objects.get(fk_paciente=p, mes_competencia=self.COMP)
        self.assertEqual(nota.valor, Decimal("400"))       # soma real (decisão #3)
        self.assertEqual(nota.status_nfs, NotaFiscal.PENDENTE)

    def test_credito_fora_do_mes_nao_entra(self):
        p = paciente("Joao", valor="200")
        credito(p, "200", date(2026, 8, 31), fitid="a")    # mês anterior
        credito(p, "200", date(2026, 10, 1), fitid="b")    # mês seguinte
        res = gerar_notas_do_mes(self.COMP)
        self.assertEqual(res.criadas, 0)

    def test_isento_valor_zero_nao_gera(self):
        p = paciente("Prefeitura", valor="0")
        credito(p, "0", fitid="a")
        res = gerar_notas_do_mes(self.COMP)
        self.assertEqual(res.isentos, 1)
        self.assertEqual(res.criadas, 0)

    def test_sem_cpf_nao_gera_e_vai_para_lista(self):
        p = paciente("Sem CPF", valor="200", cpf="")
        credito(p, "200", fitid="a")
        res = gerar_notas_do_mes(self.COMP)
        self.assertEqual(res.criadas, 0)
        self.assertIn("Sem CPF", res.sem_cpf)

    def test_nao_conciliado_nao_conta(self):
        p = paciente("Joao", valor="200")
        t = credito(p, "200", fitid="a")
        t.status_conciliacao = TransacaoOFX.NAO_IDENTIFICADO
        t.save(update_fields=["status_conciliacao"])
        res = gerar_notas_do_mes(self.COMP)
        self.assertEqual(res.criadas, 0)

    def test_idempotente_nao_duplica(self):
        p = paciente("Joao", valor="200")
        credito(p, "200", fitid="a")
        gerar_notas_do_mes(self.COMP)
        res2 = gerar_notas_do_mes(self.COMP)
        self.assertEqual(res2.criadas, 0)
        self.assertEqual(res2.ja_existiam, 1)
        self.assertEqual(NotaFiscal.objects.filter(fk_paciente=p).count(), 1)

    def test_refechamento_atualiza_valor_de_nota_pendente(self):
        p = paciente("Joao", valor="200")
        credito(p, "200", date(2026, 9, 5), fitid="a")
        gerar_notas_do_mes(self.COMP)
        credito(p, "100", date(2026, 9, 25), fitid="b")   # mais um crédito
        gerar_notas_do_mes(self.COMP)
        nota = NotaFiscal.objects.get(fk_paciente=p, mes_competencia=self.COMP)
        self.assertEqual(nota.valor, Decimal("300"))


class UniqueTogetherTest(TestCase):
    def test_uma_nota_por_paciente_por_mes(self):
        p = paciente("Joao")
        NotaFiscal.objects.create(fk_paciente=p, mes_competencia=date(2026, 9, 1),
                                  valor=Decimal("200"))
        with self.assertRaises(IntegrityError):
            NotaFiscal.objects.create(fk_paciente=p, mes_competencia=date(2026, 9, 1),
                                      valor=Decimal("200"))


class MontarNfsInfoTest(TestCase):
    def _nota(self, valor="200", cpf="52998224725"):
        p = paciente("Joao", cpf=cpf)
        return NotaFiscal.objects.create(
            fk_paciente=p, mes_competencia=date(2026, 9, 1), valor=Decimal(valor))

    def test_discriminacao_tem_texto_de_imunidade(self):
        info = _montar_nfs_info(self._nota())
        self.assertIn(TEXTO_IMUNIDADE, info["servico"]["discriminacao"])
        self.assertEqual(info["servico"]["valor_servicos"], "200.00")

    def test_valor_zero_vira_centavo_com_desconto(self):
        info = _montar_nfs_info(self._nota(valor="0"))
        self.assertEqual(info["servico"]["valor_servicos"], "0.01")
        self.assertEqual(info["servico"]["desconto_incondicionado"], "0.01")

    def test_tomador_presente_quando_tem_cpf(self):
        info = _montar_nfs_info(self._nota())
        self.assertEqual(info["tomador"]["cpf"], "52998224725")

    def test_sem_cpf_nao_monta_tomador(self):
        info = _montar_nfs_info(self._nota(cpf=""))
        self.assertNotIn("tomador", info)


class FakeWebmania:
    """Dublê do cliente Webmania (a assinatura real está inativa)."""
    def __init__(self, resultado):
        self.resultado = resultado
        self.enviados = []

    def send_nfs(self, nfs_info):
        self.enviados.append(nfs_info)
        return self.resultado


class EmitirNotaTest(TestCase):
    def _nota(self, cpf="52998224725", valor="200"):
        p = paciente("Joao", cpf=cpf, valor=valor)
        return NotaFiscal.objects.create(
            fk_paciente=p, mes_competencia=date(2026, 9, 1), valor=Decimal(valor))

    def test_sem_cpf_marca_erro_sem_chamar_api(self):
        nota = self._nota(cpf="")
        api = FakeWebmania({"status": "aprovado", "uuid": "x"})
        ok, _ = _emitir_nota(nota, api=api)
        self.assertFalse(ok)
        nota.refresh_from_db()
        self.assertEqual(nota.status_nfs, NotaFiscal.ERRO)
        self.assertEqual(api.enviados, [])

    def test_aprovado_vira_processando_com_uuid(self):
        nota = self._nota()
        api = FakeWebmania({"status": "aprovado", "uuid": "uuid-123"})
        ok, _ = _emitir_nota(nota, api=api)
        self.assertTrue(ok)
        nota.refresh_from_db()
        self.assertEqual(nota.status_nfs, NotaFiscal.PROCESSANDO)
        self.assertEqual(nota.id_nfs, "uuid-123")

    def test_erro_da_api_marca_erro_com_motivo(self):
        nota = self._nota()
        api = FakeWebmania({"status": "erro", "log": {"errors": ["subscription_inactive"]}})
        ok, _ = _emitir_nota(nota, api=api)
        self.assertFalse(ok)
        nota.refresh_from_db()
        self.assertEqual(nota.status_nfs, NotaFiscal.ERRO)
        self.assertIn("subscription_inactive", nota.motivo_erro)

    def test_sem_token_configurado_nao_estoura_500(self):
        nota = self._nota()
        # Webmania() levanta ValueError sem WEBMANIA_API_TOKEN → erro amigável.
        with patch("fiscal.views.Webmania", side_effect=ValueError("sem token")):
            ok, msg = _emitir_nota(nota)
        self.assertFalse(ok)
        nota.refresh_from_db()
        self.assertEqual(nota.status_nfs, NotaFiscal.ERRO)
        self.assertIn("sem token", msg)


class PainelViewTest(TestCase):
    def setUp(self):
        self.gestor = User.objects.create_user("gestor", password="x", is_staff=True)
        self.client.force_login(self.gestor)

    def test_painel_responde_200(self):
        r = self.client.get("/notas/?mes=2026-09")
        self.assertEqual(r.status_code, 200)

    def test_fechar_mes_cria_notas(self):
        p = paciente("Joao", valor="200")
        credito(p, "200", date(2026, 9, 10), fitid="a")
        self.client.post("/notas/fechar-mes/", {"mes": "2026-09"})
        self.assertTrue(
            NotaFiscal.objects.filter(fk_paciente=p, mes_competencia=date(2026, 9, 1)).exists())

    def test_exige_staff(self):
        self.client.logout()
        self.client.force_login(User.objects.create_user("ana", password="x"))
        r = self.client.get("/notas/")
        self.assertNotEqual(r.status_code, 200)
