"""
Alerta de pagamento abaixo do mínimo (D14b, decisões #15 revisada / #21).

Quando um crédito casa com um paciente mas o valor fica **abaixo do mínimo
global** (R$ 200), avisa in-system **só o terapeuta** do paciente, para ele
conversar e acertar o valor na faixa de R$ 200 a R$ 250. WhatsApp é fase 2.
A flag ``valor_divergente`` da transação passa a significar "abaixo do mínimo".
"""
from principais.models import Notificacao

from conciliacao.regras import VALOR_FAIXA_MAX, VALOR_MINIMO


def _texto(trans):
    nome = trans.fk_paciente.nome
    return (
        f"{nome} pagou R$ {trans.valor} em {trans.data:%d/%m/%Y}, abaixo do "
        f"mínimo de R$ {VALOR_MINIMO}. Converse com o paciente e acerte o valor "
        f"entre R$ {VALOR_MINIMO} e R$ {VALOR_FAIXA_MAX}. "
        f"(A nota sai pelo valor real recebido.)"
    )


def notificar_divergencia(trans):
    """Cria o alerta in-system para o terapeuta do paciente quando o pagamento
    ficou abaixo do mínimo. Retorna quantas notificações foram criadas."""
    paciente = trans.fk_paciente
    if paciente is None or not trans.valor_divergente:
        return 0
    terapeuta = paciente.fk_terapeuta
    if terapeuta is None:
        return 0

    Notificacao.objects.create(destinatario=terapeuta.fk_associado, texto=_texto(trans))
    return 1


def notificar_divergencias_do_extrato(extrato):
    """Gera os alertas de todas as transações abaixo do mínimo do extrato."""
    total = 0
    for trans in extrato.transacoes.filter(valor_divergente=True).select_related(
        'fk_paciente__fk_terapeuta__fk_associado',
    ):
        total += notificar_divergencia(trans)
    return total
