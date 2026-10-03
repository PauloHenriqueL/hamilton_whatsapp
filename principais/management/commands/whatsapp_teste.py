"""Envia uma mensagem de teste pelo WhatsApp (valida credenciais/porte).

Uso:
  python manage.py whatsapp_teste --numero 5531830551118 --texto "Olá do Hamilton"

Em dry-run (padrão) só registra no log. Para enviar de verdade:
  WHATSAPP_DRY_RUN=false WHATSAPP_TOKEN=... WHATSAPP_PHONE_NUMBER_ID=... \
    python manage.py whatsapp_teste --numero 5531830551118

Se WHATSAPP_TEST_NUMBER estiver definido, o destino é sempre ele.
"""
from django.core.management.base import BaseCommand

from principais.whatsapp import enviar_whatsapp


class Command(BaseCommand):
    help = "Envia uma mensagem de teste pelo WhatsApp (dry-run por padrão)."

    def add_arguments(self, parser):
        parser.add_argument("--numero", default="", help="Telefone destino (ex.: 5531830551118)")
        parser.add_argument("--texto", default="Mensagem de teste do Hamilton 2.0.")

    def handle(self, *args, **opts):
        numero = opts["numero"] or "5531830551118"
        ok = enviar_whatsapp(numero, opts["texto"])
        if ok:
            self.stdout.write(self.style.SUCCESS(
                "Envio OK (ou simulado em dry-run). Veja o log para detalhes."))
        else:
            self.stdout.write(self.style.ERROR("Falha no envio. Veja o log."))
