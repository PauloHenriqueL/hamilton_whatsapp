"""Envia lembretes de sessão ~1h antes (para terapeuta e paciente).

Pensado para rodar de tempos em tempos via cron (ex.: a cada 15 min). A cada
execução, procura as sessões semanais que começam dentro da janela
``(antecedencia - janela, antecedencia]`` minutos a partir de agora e dispara
o lembrete uma única vez (desde que a cadência do cron == --janela).

Uso:
  python manage.py enviar_lembretes_sessao            # antecedência 60, janela 15
  python manage.py enviar_lembretes_sessao --antecedencia 60 --janela 15 --simular
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from principais.models import SessaoSemanal
from principais.whatsapp_mensagens import lembrar_sessao


class Command(BaseCommand):
    help = "Envia lembretes das sessões que começam em ~1h (rodar via cron)."

    def add_arguments(self, parser):
        parser.add_argument("--antecedencia", type=int, default=60,
                            help="Minutos antes da sessão para avisar (padrão 60).")
        parser.add_argument("--janela", type=int, default=15,
                            help="Largura da janela em min = cadência do cron (padrão 15).")
        parser.add_argument("--simular", action="store_true",
                            help="Só lista; não envia nem cria notificações.")

    def handle(self, *args, **o):
        agora = timezone.localtime()
        antec, janela = o["antecedencia"], o["janela"]
        sessoes = SessaoSemanal.objects.filter(
            dia_semana=agora.weekday(),
            fk_paciente__is_active=True,
            fk_paciente__fk_terapeuta__isnull=False,
        ).select_related("fk_paciente__fk_terapeuta__fk_associado")

        total = 0
        for s in sessoes:
            inicio = agora.replace(hour=s.hora_inicio.hour, minute=s.hora_inicio.minute,
                                   second=0, microsecond=0)
            delta_min = (inicio - agora).total_seconds() / 60
            if not (antec - janela < delta_min <= antec):
                continue
            total += 1
            label = (f"{s.fk_paciente.nome} às {s.hora_inicio:%H:%M} "
                     f"(em {int(delta_min)} min)")
            if o["simular"]:
                self.stdout.write(f"  [simular] lembrete: {label}")
            else:
                lembrar_sessao(s)
                self.stdout.write(f"  lembrete disparado: {label}")

        self.stdout.write(self.style.SUCCESS(f"{total} sessão(ões) na janela."))
