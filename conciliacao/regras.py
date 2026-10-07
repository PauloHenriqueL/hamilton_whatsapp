"""Regras de valor da conciliação (alerta de pagamento abaixo do mínimo).

Decisão (07/10/2026): o valor esperado é um padrão global — faixa aceitável de
R$ 200 a R$ 250. Quem paga **abaixo de R$ 200** gera um alerta para o terapeuta
negociar com o paciente e acertar o valor dentro da faixa. Pagar R$ 200 ou mais
(inclusive acima de 250) não gera alerta. Isento (vlr_sessao 0) nunca alerta.

Isto **revisa a decisão #15** (antes: qualquer diferença do combinado alertava
terapeuta + supervisor; agora: só abaixo do mínimo, e só o terapeuta). A nota
continua saindo pelo valor real do OFX (decisão #3, intacta).
"""
import calendar
from datetime import date
from decimal import Decimal

VALOR_MINIMO = Decimal('200')
VALOR_FAIXA_MAX = Decimal('250')

# Carência (dias) depois do dia esperado antes de considerar o pagamento atrasado.
CARENCIA_ATRASO_DIAS = 5


def esta_em_atraso(paciente, pago_no_mes, referencia=None):
    """Indica se o paciente está atrasado NO MÊS de ``referencia`` (expectativa,
    não prova — decisão #3). ``pago_no_mes`` diz se há crédito conciliado dele no
    mês (quem calcula isso é a view, para não consultar o banco aqui).

    Atraso = tem data esperada, já passou do dia esperado + carência e ainda não
    há crédito no mês. Sem data cadastrada → nunca acusa atraso."""
    if not paciente.data_primeiro_pagamento:
        return False
    ref = referencia or date.today()
    dia_esperado = paciente.dia_pagamento_esperado
    ultimo_dia = calendar.monthrange(ref.year, ref.month)[1]
    dia_no_mes = min(dia_esperado, ultimo_dia)   # ex.: espera dia 31 em fevereiro
    if ref.day <= dia_no_mes + CARENCIA_ATRASO_DIAS:
        return False                              # ainda dentro da carência
    return not pago_no_mes


def abaixo_do_minimo(paciente, valor):
    """True se o crédito conciliado está abaixo do mínimo e deve alertar.
    Isento (vlr_sessao 0) não alerta."""
    if paciente is None or paciente.vlr_sessao == 0:
        return False
    return valor < VALOR_MINIMO
