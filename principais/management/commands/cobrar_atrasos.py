"""Cobra pagamentos em atraso (escalonado por meses em aberto).

Fonte da verdade: o OFX conciliado. Um paciente "pagou" o mês M se existe uma
TransacaoOFX CONCILIADA com data em M. Rodar depois de importar o OFX do mês
passado (até ~dia 10). Escalonamento: 1 mês -> terapeuta; 2 -> + supervisor;
3 -> + gestor(es).

Para não gerar falso-positivo antes do upload, um mês só conta como "não pago"
se houver ALGUM crédito conciliado naquele mês (ou seja, o OFX daquele mês já
foi importado).

Uso:
  python manage.py cobrar_atrasos                 # referência = mês passado
  python manage.py cobrar_atrasos --mes 2026-09   # referência explícita
  python manage.py cobrar_atrasos --simular       # só lista, não cobra
"""
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from conciliacao.models import TransacaoOFX
from principais.models import Paciente
from principais.whatsapp_mensagens import cobrar_atraso

MAX_MESES = 3  # escalonamento vai até o gestor em 3 meses


def _mes_anterior(ano, mes):
    return (ano - 1, 12) if mes == 1 else (ano, mes - 1)


class Command(BaseCommand):
    help = "Cobra pagamentos em atraso via WhatsApp + in-system (rodar após o OFX)."

    def add_arguments(self, parser):
        parser.add_argument("--mes", default="", help="Mês de referência YYYY-MM (padrão: mês passado).")
        parser.add_argument("--simular", action="store_true", help="Só lista; não cobra.")

    def handle(self, *args, **o):
        if o["mes"]:
            try:
                ano, mes = map(int, o["mes"].split("-"))
                date(ano, mes, 1)
            except (ValueError, TypeError):
                raise CommandError("Use --mes YYYY-MM, ex.: 2026-09.")
        else:
            hoje = date.today()
            ano, mes = _mes_anterior(hoje.year, hoje.month)

        self.stdout.write(f"Referência: {mes:02d}/{ano}")
        pacientes = (Paciente.objects
                     .filter(is_active=True, fk_terapeuta__isnull=False, vlr_sessao__gt=0)
                     .select_related("fk_terapeuta__fk_associado",
                                     "fk_terapeuta__fk_supervisor__fk_associado"))
        total = 0
        for p in pacientes:
            meses = self._meses_em_aberto(p, ano, mes)
            if meses < 1:
                continue
            total += 1
            if o["simular"]:
                self.stdout.write(f"  [simular] {p.nome}: {meses} mês(es) em aberto")
            else:
                n = cobrar_atraso(p, meses)
                self.stdout.write(f"  cobrado {p.nome}: {meses} mês(es) -> {n} destinatário(s)")
        self.stdout.write(self.style.SUCCESS(f"{total} paciente(s) em atraso."))

    def _meses_em_aberto(self, paciente, ano, mes):
        """Conta meses consecutivos sem pagamento, do mês de referência para
        trás, só enquanto houver dados de OFX daquele mês. Teto = MAX_MESES."""
        count = 0
        a, m = ano, mes
        while count < MAX_MESES:
            if not self._tem_dados(a, m):
                break  # sem OFX daquele mês -> não dá para afirmar atraso
            if self._pagou(paciente, a, m):
                break  # pagou -> encerra a sequência de atraso
            count += 1
            a, m = _mes_anterior(a, m)
        return count

    @staticmethod
    def _pagou(paciente, ano, mes):
        return TransacaoOFX.objects.filter(
            fk_paciente=paciente, status_conciliacao=TransacaoOFX.CONCILIADO,
            data__year=ano, data__month=mes).exists()

    @staticmethod
    def _tem_dados(ano, mes):
        return TransacaoOFX.objects.filter(
            status_conciliacao=TransacaoOFX.CONCILIADO,
            data__year=ano, data__month=mes).exists()
