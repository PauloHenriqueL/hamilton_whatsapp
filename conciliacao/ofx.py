"""
Parser tolerante de OFX (D13).

O arquivo é SGML (OFXSGML/1.02), muitas vezes com tags sem fechamento
(``<TAG>valor`` até a próxima ``<``) e encoding cp1252. Lemos só os créditos
(``TRNTYPE=CREDIT``) e guardamos o nome do pagador cru e normalizado — o
``<NAME>`` vem com o prefixo fixo "Recebimento Pix" e às vezes truncado (D13).
"""
import hashlib
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation

# Bloco de uma transação, com ou sem </STMTTRN> de fechamento.
_STMTTRN_RE = re.compile(r"<STMTTRN>(.*?)(?:</STMTTRN>|(?=<STMTTRN>)|\Z)", re.DOTALL | re.IGNORECASE)
_ACCTID_RE = re.compile(r"<ACCTID>([^<\r\n]+)", re.IGNORECASE)

PREFIXO_PIX = re.compile(r"^\s*recebimento\s+pix\s+", re.IGNORECASE)


def _tag(bloco, tag):
    """Valor de uma tag SGML, tolerante à ausência de fechamento."""
    m = re.search(rf"<{tag}>([^<\r\n]*)", bloco, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _parse_data(raw):
    """DTPOSTED tipo '20260831120000[-3:BRT]' → date."""
    m = re.match(r"(\d{4})(\d{2})(\d{2})", raw or "")
    if not m:
        return None
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def normalizar_nome(nome):
    """Remove o prefixo 'Recebimento Pix', acentos e caixa — chave de match."""
    if not nome:
        return ""
    sem_prefixo = PREFIXO_PIX.sub("", nome)
    sem_acento = unicodedata.normalize("NFKD", sem_prefixo).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


def hash_conteudo(conteudo_bytes):
    return hashlib.sha256(conteudo_bytes).hexdigest()


def decodificar(conteudo_bytes):
    """Decodifica cp1252 (CHARSET:1252), com fallback tolerante."""
    for enc in ("cp1252", "latin-1", "utf-8"):
        try:
            return conteudo_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return conteudo_bytes.decode("cp1252", errors="replace")


def parse_creditos(texto):
    """Extrai os créditos do OFX. Retorna lista de dicts (uma por crédito) e o
    ACCTID da conta."""
    acct_m = _ACCTID_RE.search(texto)
    conta = acct_m.group(1).strip() if acct_m else None

    creditos = []
    for bloco in _STMTTRN_RE.findall(texto):
        if _tag(bloco, "TRNTYPE").upper() != "CREDIT":
            continue
        fitid = _tag(bloco, "FITID")
        if not fitid:
            continue
        try:
            valor = Decimal(_tag(bloco, "TRNAMT").replace(",", "."))
        except (InvalidOperation, ValueError):
            continue
        nome = _tag(bloco, "NAME")
        creditos.append({
            "fitid": fitid,
            "data": _parse_data(_tag(bloco, "DTPOSTED")),
            "valor": valor,
            "nome_pagador": nome,
            "nome_normalizado": normalizar_nome(nome),
            "memo": _tag(bloco, "MEMO"),
        })
    return creditos, conta
