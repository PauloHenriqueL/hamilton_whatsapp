"""Cria os templates de WhatsApp na Meta via Message Template API.

Evita ter que cadastrar à mão no Gerenciador de Modelos. Submete os 3 templates
(lembrete paciente, lembrete terapeuta, cobrança) para aprovação da Meta.

Pré-requisitos:
- WHATSAPP_TOKEN com permissão ``whatsapp_business_management``.
- WHATSAPP_WABA_ID = id da WhatsApp Business Account (não é o phone_number_id;
  pegue no Gerenciador do WhatsApp → Configurações, ou no mesmo WABA do Sofia).

Uso:
  python manage.py criar_templates_whatsapp            # dry-run: só mostra os payloads
  python manage.py criar_templates_whatsapp --enviar   # cria de verdade na Meta

Doc: https://developers.facebook.com/docs/whatsapp/business-management-api/message-templates
"""
import json
import os

import requests
from django.core.management.base import BaseCommand

from principais.whatsapp import GRAPH_API_BASE
from principais.whatsapp_mensagens import (
    TPL_COBRANCA, TPL_LEMBRETE_PACIENTE, TPL_LEMBRETE_TERAPEUTA,
)

TEMPLATES = [
    {
        "name": TPL_LEMBRETE_PACIENTE,
        "language": "pt_BR",
        "category": "UTILITY",
        "components": [{
            "type": "BODY",
            "text": ("Olá, {{1}}! Passando para lembrar da sua sessão hoje às "
                     "{{2}} com {{3}}.\n\nSe precisar remarcar, fale com a "
                     "Clínica Allos. Até já!"),
            "example": {"body_text": [["Mariana Souza", "14:00", "Ana Terapeuta"]]},
        }],
    },
    {
        "name": TPL_LEMBRETE_TERAPEUTA,
        "language": "pt_BR",
        "category": "UTILITY",
        "components": [{
            "type": "BODY",
            "text": ("Olá, {{1}}! Lembrete: você tem sessão hoje às {{2}} com o "
                     "paciente {{3}}. Bom atendimento!"),
            "example": {"body_text": [["Ana Terapeuta", "14:00", "Mariana Souza"]]},
        }],
    },
    {
        "name": TPL_COBRANCA,
        "language": "pt_BR",
        "category": "UTILITY",
        "components": [{
            "type": "BODY",
            "text": ("Olá, {{1}}. O paciente {{2}} está com {{3}} mês(es) de "
                     "pagamento em aberto.\n\nPor favor, verifique e faça a "
                     "cobrança. — Clínica Allos"),
            "example": {"body_text": [["Ana Terapeuta", "João Pereira", "2"]]},
        }],
    },
]


class Command(BaseCommand):
    help = "Cria os templates de WhatsApp na Meta (dry-run por padrão)."

    def add_arguments(self, parser):
        parser.add_argument("--enviar", action="store_true",
                            help="Cria de verdade na Meta (senão só mostra os payloads).")

    def handle(self, *args, **o):
        token = os.getenv("WHATSAPP_TOKEN", "")
        waba_id = os.getenv("WHATSAPP_WABA_ID", "")

        if not o["enviar"]:
            self.stdout.write("DRY-RUN (use --enviar para criar na Meta):\n")
            for t in TEMPLATES:
                self.stdout.write(json.dumps(t, ensure_ascii=False, indent=2))
            return

        if not token or not waba_id:
            self.stdout.write(self.style.ERROR(
                "Defina WHATSAPP_TOKEN e WHATSAPP_WABA_ID no .env."))
            return

        url = f"{GRAPH_API_BASE}/{waba_id}/message_templates"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        for t in TEMPLATES:
            try:
                r = requests.post(url, json=t, headers=headers, timeout=20)
                data = r.json()
            except requests.RequestException as e:
                self.stdout.write(self.style.ERROR(f"{t['name']}: falha de rede {e}"))
                continue
            if r.ok:
                self.stdout.write(self.style.SUCCESS(
                    f"{t['name']}: criado (id={data.get('id')}, status={data.get('status')})"))
            else:
                erro = (data.get("error") or {}).get("message", data)
                self.stdout.write(self.style.ERROR(f"{t['name']}: {erro}"))
