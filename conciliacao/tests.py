"""Testes da conciliação (D13–D15, D14b).

Cobrem o parser tolerante de OFX, a normalização do nome do pagador, o motor de
conciliação por nome + valor (incluindo a flag de divergência — decisão #15), a
notificação in-system ao terapeuta/supervisor (D14b) e as views de importação
(idempotência por hash do arquivo + fitid — decisão #10) e associação manual.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from principais.models import (
    Associado, Notificacao, PagadorAlternativo, Paciente, Terapeuta)

from conciliacao import ofx as ofx_parser
from conciliacao.matching import conciliar_extrato, conciliar_transacao
from conciliacao.models import ExtratoOFX, TransacaoOFX
from conciliacao.notificacoes import notificar_divergencia


def cria_terapeuta(nome, username=None, supervisor=None):
    user = User.objects.create_user(username=username, password="x") if username else None
    assoc = Associado.objects.create(nome=nome, telefone="31988550000", usuario=user)
    return Terapeuta.objects.create(fk_associado=assoc, fk_supervisor=supervisor)


def paciente(nome, valor="200", ter=None, ativo=True):
    return Paciente.objects.create(
        nome=nome, telefone="31977770000", vlr_sessao=Decimal(valor),
        fk_terapeuta=ter, is_active=ativo)


def extrato():
    return ExtratoOFX.objects.create(arquivo_nome="x.ofx", hash_arquivo="h-abc")


def trans(ext, nome, valor="200", fitid="f1", quando=date(2026, 9, 15)):
    return TransacaoOFX.objects.create(
        fk_extrato=ext, fitid=fitid, data=quando, valor=Decimal(valor),
        nome_pagador=nome, nome_normalizado=ofx_parser.normalizar_nome(nome))


# ------------------------------------------------------------------ parser OFX
class NormalizarNomeTest(TestCase):
    def test_remove_prefixo_pix_acentos_e_caixa(self):
        n = ofx_parser.normalizar_nome
        self.assertEqual(n("Recebimento Pix João da Silva"), "joao da silva")
        self.assertEqual(n("RECEBIMENTO PIX  MARÍA  JOSÉ"), "maria jose")
        self.assertEqual(n("José Antônio"), "jose antonio")

    def test_nome_vazio(self):
        self.assertEqual(ofx_parser.normalizar_nome(""), "")
        self.assertEqual(ofx_parser.normalizar_nome(None), "")


OFX_EXEMPLO = """OFXHEADER:100
DATA:OFXSGML
CHARSET:1252
<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS>
<BANKACCTFROM><ACCTID>12345-6</ACCTID></BANKACCTFROM>
<BANKTRANLIST>
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20260915120000[-3:BRT]
<TRNAMT>200.00
<FITID>CRED-1
<NAME>Recebimento Pix Joao Pereira
<MEMO>Pix recebido
</STMTTRN>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20260916120000[-3:BRT]
<TRNAMT>-50.00
<FITID>DEB-1
<NAME>Tarifa
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20260917120000
<TRNAMT>150,00
<FITID>CRED-2
<NAME>Recebimento Pix Maria Souza
</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>
"""


class ParseCreditosTest(TestCase):
    def test_le_so_creditos_e_ignora_debito(self):
        creditos, conta = ofx_parser.parse_creditos(OFX_EXEMPLO)
        self.assertEqual(conta, "12345-6")
        self.assertEqual(len(creditos), 2)            # o DEBIT é ignorado
        self.assertEqual({c["fitid"] for c in creditos}, {"CRED-1", "CRED-2"})

    def test_campos_do_credito(self):
        creditos, _ = ofx_parser.parse_creditos(OFX_EXEMPLO)
        c = next(c for c in creditos if c["fitid"] == "CRED-1")
        self.assertEqual(c["data"], date(2026, 9, 15))
        self.assertEqual(c["valor"], Decimal("200.00"))
        self.assertEqual(c["nome_pagador"], "Recebimento Pix Joao Pereira")
        self.assertEqual(c["nome_normalizado"], "joao pereira")

    def test_valor_com_virgula_e_tag_sem_fechamento(self):
        """CRED-2 usa vírgula decimal e o bloco não tem </STMTTRN>."""
        creditos, _ = ofx_parser.parse_creditos(OFX_EXEMPLO)
        c = next(c for c in creditos if c["fitid"] == "CRED-2")
        self.assertEqual(c["valor"], Decimal("150.00"))

    def test_hash_deterministico(self):
        b = "qualquer".encode()
        self.assertEqual(ofx_parser.hash_conteudo(b), ofx_parser.hash_conteudo(b))
        self.assertNotEqual(ofx_parser.hash_conteudo(b), ofx_parser.hash_conteudo(b"outro"))

    def test_decodifica_cp1252(self):
        texto = ofx_parser.decodificar("Jo\xe3o".encode("cp1252"))
        self.assertEqual(texto, "João")


# ------------------------------------------------------------------- matching
class ConciliarTransacaoTest(TestCase):
    def setUp(self):
        self.ext = extrato()

    def test_match_exato_por_nome(self):
        p = paciente("João Pereira", valor="200")
        t = trans(self.ext, "Recebimento Pix João Pereira", valor="200")
        escolhido = conciliar_transacao(t)
        self.assertEqual(escolhido, p)
        t.refresh_from_db()
        self.assertEqual(t.status_conciliacao, TransacaoOFX.CONCILIADO)
        self.assertFalse(t.valor_divergente)

    def test_sem_match_vai_para_fila(self):
        paciente("Outro Nome")
        t = trans(self.ext, "Recebimento Pix Desconhecido")
        self.assertIsNone(conciliar_transacao(t))
        t.refresh_from_db()
        self.assertEqual(t.status_conciliacao, TransacaoOFX.NAO_IDENTIFICADO)

    def test_valor_divergente_concilia_com_flag(self):
        """Nome bate, valor difere → concilia pelo valor real + flag (decisão #15)."""
        paciente("Carla Dias", valor="200")
        t = trans(self.ext, "Recebimento Pix Carla Dias", valor="180")
        self.assertIsNotNone(conciliar_transacao(t))
        t.refresh_from_db()
        self.assertEqual(t.status_conciliacao, TransacaoOFX.CONCILIADO)
        self.assertTrue(t.valor_divergente)

    def test_homonimos_desambigua_por_valor(self):
        p1 = paciente("Ana Paula", valor="200")
        paciente("Ana Paula", valor="300")
        t = trans(self.ext, "Recebimento Pix Ana Paula", valor="200")
        self.assertEqual(conciliar_transacao(t), p1)

    def test_homonimos_mesmo_valor_fica_na_fila(self):
        paciente("Ana Paula", valor="200")
        paciente("Ana Paula", valor="200")
        t = trans(self.ext, "Recebimento Pix Ana Paula", valor="200")
        self.assertIsNone(conciliar_transacao(t))
        t.refresh_from_db()
        self.assertEqual(t.status_conciliacao, TransacaoOFX.NAO_IDENTIFICADO)

    def test_paciente_inativo_nao_entra_no_indice(self):
        paciente("Inativo Silva", ativo=False)
        t = trans(self.ext, "Recebimento Pix Inativo Silva")
        self.assertIsNone(conciliar_transacao(t))


class ConciliarExtratoTest(TestCase):
    def test_contagem_conciliadas_divergentes_nao_id(self):
        ext = extrato()
        paciente("Joao Um", valor="200")
        paciente("Maria Dois", valor="200")
        trans(ext, "Recebimento Pix Joao Um", valor="200", fitid="a")
        trans(ext, "Recebimento Pix Maria Dois", valor="150", fitid="b")  # divergente
        trans(ext, "Recebimento Pix Fantasma", valor="200", fitid="c")    # fila
        conciliadas, divergentes, nao_id = conciliar_extrato(ext)
        self.assertEqual((conciliadas, divergentes, nao_id), (2, 1, 1))


# ----------------------------------------------------------------- notificação
class NotificarDivergenciaTest(TestCase):
    def setUp(self):
        self.ext = extrato()
        self.sup = cria_terapeuta("Supervisor")
        self.ter = cria_terapeuta("Terapeuta", supervisor=self.sup)
        self.pac = paciente("Bruno Lima", valor="200", ter=self.ter)

    def test_divergencia_notifica_terapeuta_e_supervisor(self):
        t = trans(self.ext, "Recebimento Pix Bruno Lima", valor="150")
        conciliar_transacao(t)
        self.assertEqual(notificar_divergencia(t), 2)
        self.assertEqual(
            Notificacao.objects.filter(destinatario=self.ter.fk_associado).count(), 1)
        self.assertEqual(
            Notificacao.objects.filter(destinatario=self.sup.fk_associado).count(), 1)

    def test_sem_divergencia_nao_notifica(self):
        t = trans(self.ext, "Recebimento Pix Bruno Lima", valor="200")
        conciliar_transacao(t)
        self.assertEqual(notificar_divergencia(t), 0)

    def test_sem_terapeuta_nao_notifica(self):
        solto = paciente("Sem Ter", valor="200")
        t = trans(self.ext, "Recebimento Pix Sem Ter", valor="150")
        conciliar_transacao(t)
        self.assertEqual(notificar_divergencia(t), 0)


# ---------------------------------------------------------------------- views
class ImportarOFXViewTest(TestCase):
    def setUp(self):
        self.gestor = User.objects.create_user("gestor", password="x", is_staff=True)
        self.client.force_login(self.gestor)

    def _upload(self, conteudo=OFX_EXEMPLO, nome="extrato.ofx"):
        arq = SimpleUploadedFile(nome, conteudo.encode("cp1252"),
                                 content_type="application/x-ofx")
        return self.client.post("/conciliacao/importar/", {"arquivo": arq}, follow=True)

    def test_importa_e_concilia(self):
        paciente("Joao Pereira", valor="200")
        self._upload()
        self.assertEqual(ExtratoOFX.objects.count(), 1)
        self.assertEqual(TransacaoOFX.objects.count(), 2)
        t = TransacaoOFX.objects.get(fitid="CRED-1")
        self.assertEqual(t.status_conciliacao, TransacaoOFX.CONCILIADO)

    def test_reimportar_mesmo_arquivo_e_bloqueado(self):
        self._upload()
        self._upload()  # idêntico → barrado pelo hash
        self.assertEqual(ExtratoOFX.objects.count(), 1)

    def test_fitid_repetido_nao_duplica(self):
        """Arquivo diferente (hash diferente), mas com um FITID já visto."""
        self._upload()
        base = TransacaoOFX.objects.count()
        # Mesmo FITID CRED-1, conteúdo levemente diferente → hash novo.
        self._upload(conteudo=OFX_EXEMPLO + "\n<!-- v2 -->")
        self.assertEqual(TransacaoOFX.objects.count(), base)  # nenhum crédito novo

    def test_exige_staff(self):
        self.client.logout()
        terapeuta_user = User.objects.create_user("ana", password="x")
        self.client.force_login(terapeuta_user)
        r = self.client.post("/conciliacao/importar/", {})
        self.assertEqual(r.status_code, 302)  # staff_member_required → login do admin


class PagadorAlternativoMatchingTest(TestCase):
    """Fallback do matching para pagadores alternativos (mãe/pai que paga o Pix)."""
    def setUp(self):
        self.ext = extrato()

    def _pagador(self, pac, nome):
        return PagadorAlternativo.objects.create(fk_paciente=pac, nome=nome)

    def test_casa_pelo_pagador_quando_nome_proprio_nao_bate(self):
        paulo = paciente("Paulo Lima", valor="200")
        self._pagador(paulo, "Maria Aparecida")
        t = trans(self.ext, "Recebimento Pix Maria Aparecida", valor="200")
        self.assertEqual(conciliar_transacao(t), paulo)
        t.refresh_from_db()
        self.assertEqual(t.status_conciliacao, TransacaoOFX.CONCILIADO)

    def test_nome_proprio_tem_precedencia_sobre_pagador(self):
        """'rodolpho lima' é o nome de um paciente E pagador de outro: ganha o próprio."""
        rodolpho = paciente("Rodolpho Lima", valor="200")
        outro = paciente("Paulo Lima", valor="200")
        self._pagador(outro, "Rodolpho Lima")
        t = trans(self.ext, "Recebimento Pix Rodolpho Lima", valor="200")
        self.assertEqual(conciliar_transacao(t), rodolpho)

    def test_pagador_ambiguo_desambigua_por_valor(self):
        p1 = paciente("Paulo", valor="200")
        p2 = paciente("Ana", valor="150")
        self._pagador(p1, "Rodolpho Lima")
        self._pagador(p2, "Rodolpho Lima")
        t = trans(self.ext, "Recebimento Pix Rodolpho Lima", valor="200")
        self.assertEqual(conciliar_transacao(t), p1)

    def test_pagador_ambiguo_mesmo_valor_vai_para_fila(self):
        p1 = paciente("Paulo", valor="200")
        p2 = paciente("Ana", valor="200")
        self._pagador(p1, "Rodolpho Lima")
        self._pagador(p2, "Rodolpho Lima")
        t = trans(self.ext, "Recebimento Pix Rodolpho Lima", valor="200")
        self.assertIsNone(conciliar_transacao(t))
        t.refresh_from_db()
        self.assertEqual(t.status_conciliacao, TransacaoOFX.NAO_IDENTIFICADO)

    def test_pagador_de_paciente_inativo_nao_conta(self):
        inativo = paciente("Paulo", valor="200", ativo=False)
        self._pagador(inativo, "Maria Aparecida")
        t = trans(self.ext, "Recebimento Pix Maria Aparecida", valor="200")
        self.assertIsNone(conciliar_transacao(t))

    def test_nome_proprio_ambiguo_nao_cai_no_pagador(self):
        """Se o nome próprio já gera candidatos (mesmo ambíguos), não mistura
        com pagadores — vai para a fila, não para um pagador homônimo."""
        paciente("Carlos", valor="200")
        paciente("Carlos", valor="200")          # homônimos pelo nome próprio
        terceiro = paciente("Outro", valor="200")
        self._pagador(terceiro, "Carlos")
        t = trans(self.ext, "Recebimento Pix Carlos", valor="200")
        self.assertIsNone(conciliar_transacao(t))  # fila, não o 'terceiro'


class AssociarPacienteViewTest(TestCase):
    def setUp(self):
        self.gestor = User.objects.create_user("gestor", password="x", is_staff=True)
        self.client.force_login(self.gestor)
        self.ext = extrato()

    def test_associacao_manual_concilia(self):
        p = paciente("Resolvido", valor="200")
        t = trans(self.ext, "Recebimento Pix Nao Bateu", valor="200")
        self.assertEqual(t.status_conciliacao, TransacaoOFX.NAO_IDENTIFICADO)
        self.client.post(f"/conciliacao/{t.pk}/associar/", {"paciente_id": p.pk_paciente})
        t.refresh_from_db()
        self.assertEqual(t.status_conciliacao, TransacaoOFX.CONCILIADO)
        self.assertEqual(t.fk_paciente, p)

    def test_associacao_manual_divergente_notifica(self):
        ter = cria_terapeuta("Ter")
        p = paciente("Divergente", valor="200", ter=ter)
        t = trans(self.ext, "Recebimento Pix Divergente", valor="120")
        self.client.post(f"/conciliacao/{t.pk}/associar/", {"paciente_id": p.pk_paciente})
        t.refresh_from_db()
        self.assertTrue(t.valor_divergente)
        self.assertEqual(
            Notificacao.objects.filter(destinatario=ter.fk_associado).count(), 1)

    def test_associacao_manual_aprende_pagador(self):
        """Associar um crédito de nome diferente grava o pagador (decisão: auto)."""
        p = paciente("Paulo Lima", valor="200")
        t = trans(self.ext, "Recebimento Pix Maria Aparecida", valor="200")
        self.client.post(f"/conciliacao/{t.pk}/associar/", {"paciente_id": p.pk_paciente})
        self.assertTrue(p.pagadores.filter(nome="Maria Aparecida").exists())

    def test_nao_aprende_quando_nome_igual_ao_paciente(self):
        p = paciente("Joao Pereira", valor="200")
        t = trans(self.ext, "Recebimento Pix Joao Pereira", valor="200")
        self.client.post(f"/conciliacao/{t.pk}/associar/", {"paciente_id": p.pk_paciente})
        self.assertEqual(p.pagadores.count(), 0)

    def test_aprendizado_nao_duplica_pagador(self):
        p = paciente("Paulo Lima", valor="200")
        PagadorAlternativo.objects.create(fk_paciente=p, nome="Maria Aparecida")
        t = trans(self.ext, "Recebimento Pix MARIA APARECIDA", valor="200")  # caixa diferente
        self.client.post(f"/conciliacao/{t.pk}/associar/", {"paciente_id": p.pk_paciente})
        self.assertEqual(p.pagadores.filter(nome__iexact="maria aparecida").count(), 1)
