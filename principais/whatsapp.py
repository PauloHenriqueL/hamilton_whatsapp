"""Envio de WhatsApp — STUB (fase 2).

O Hamilton 2.0 ainda não tem provedor de WhatsApp contratado (Z-API, Twilio,
Evolution…). A decisão #21 diz que a notificação começa in-system; o WhatsApp
fica como ponto de extensão pronto para plugar. Esta função só registra a
intenção de envio (log) e retorna False — NÃO envia de verdade.

Para ativar: implementar a chamada ao provedor aqui e devolver True no sucesso.
"""
import logging

logger = logging.getLogger(__name__)


def enviar_whatsapp(telefone, texto):
    """STUB: registra o envio pretendido. Retorna False (não enviado)."""
    logger.info("WhatsApp (stub) para %s: %s", telefone, texto)
    return False
