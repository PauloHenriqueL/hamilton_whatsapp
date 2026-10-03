"""Envio de WhatsApp via WhatsApp Cloud API (Meta) — portado do projeto Sofia.

Mesmo provedor e formato do Sofia (``sofia/app/services/whatsapp_client.py``):
Graph API da Meta. O envio é o POST em ``/{PHONE_NUMBER_ID}/messages``.

Segurança por padrão:
- ``WHATSAPP_DRY_RUN`` começa **ligado** (true): nada é enviado de verdade,
  só registra no log. Para enviar, defina ``WHATSAPP_DRY_RUN=false`` e as
  credenciais.
- ``WHATSAPP_TEST_NUMBER``: se definido, TODAS as mensagens vão para esse
  número (modo teste), nunca para pacientes/terapeutas reais.

Env vars (ver .env.example):
- ``WHATSAPP_TOKEN``            Bearer token permanente (system user da Meta)
- ``WHATSAPP_PHONE_NUMBER_ID``  id do número na Cloud API (vai na URL)
- ``WHATSAPP_DRY_RUN``          'true' (padrão) não envia; 'false' envia
- ``WHATSAPP_TEST_NUMBER``      redireciona tudo para esse número (teste)

IMPORTANTE (janela de 24h da Meta): texto livre só chega se o destinatário
mandou mensagem nas últimas 24h. Mensagens iniciadas por nós (lembrete de
sessão, cobrança) exigem **template aprovado** — use ``enviar_template``.
"""
import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v23.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def normalizar_telefone(telefone):
    """Para o formato da Meta: só dígitos, com DDI 55. Ex.: '31988550000' ->
    '5531988550000'. Retorna None se não houver dígitos suficientes."""
    digitos = re.sub(r"\D", "", telefone or "")
    if len(digitos) < 10:
        return None
    if not digitos.startswith("55"):
        digitos = "55" + digitos
    return digitos


def _config():
    return {
        "token": os.getenv("WHATSAPP_TOKEN", ""),
        "phone_id": os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""),
        "dry_run": os.getenv("WHATSAPP_DRY_RUN", "true").strip().lower() != "false",
        "test_number": os.getenv("WHATSAPP_TEST_NUMBER", "").strip(),
    }


def _enviar(payload):
    """Choke point de envio. Aplica modo teste e dry-run. Retorna (ok, info)."""
    cfg = _config()
    if cfg["test_number"]:
        payload = {**payload, "to": normalizar_telefone(cfg["test_number"])}
    destino = payload.get("to")

    if cfg["dry_run"] or not cfg["token"] or not cfg["phone_id"]:
        motivo = "dry-run" if cfg["dry_run"] else "sem credenciais"
        logger.info("WhatsApp (%s) -> %s: %s", motivo, destino, payload)
        return True, {"dry_run": True}

    url = f"{GRAPH_API_BASE}/{cfg['phone_id']}/messages"
    try:
        r = requests.post(
            url, json=payload,
            headers={"Authorization": f"Bearer {cfg['token']}",
                     "Content-Type": "application/json"},
            timeout=20,
        )
        r.raise_for_status()
        return True, r.json()
    except requests.RequestException as e:
        corpo = getattr(e.response, "text", "")
        logger.warning("Falha ao enviar WhatsApp para %s: %s %s", destino, e, corpo)
        return False, {"erro": str(e)}


def enviar_whatsapp(telefone, texto):
    """Texto livre (só funciona dentro da janela de 24h). Retorna True se
    enviado (ou simulado em dry-run), False em falha/numero inválido."""
    to = normalizar_telefone(telefone)
    if not to:
        logger.warning("WhatsApp: telefone inválido %r", telefone)
        return False
    ok, _ = _enviar({
        "messaging_product": "whatsapp", "recipient_type": "individual",
        "to": to, "type": "text", "text": {"body": texto},
    })
    return ok


def enviar_template(telefone, template, parametros=None, lang="pt_BR"):
    """Template aprovado pela Meta (HSM) — para mensagens que nós iniciamos
    (lembrete de sessão, cobrança), fora da janela de 24h. ``parametros`` são
    os valores das variáveis {{1}}, {{2}}... do corpo do template."""
    to = normalizar_telefone(telefone)
    if not to:
        logger.warning("WhatsApp: telefone inválido %r", telefone)
        return False
    componentes = []
    if parametros:
        componentes = [{
            "type": "body",
            "parameters": [{"type": "text", "text": str(p)} for p in parametros],
        }]
    ok, _ = _enviar({
        "messaging_product": "whatsapp", "to": to, "type": "template",
        "template": {"name": template, "language": {"code": lang},
                     "components": componentes},
    })
    return ok
