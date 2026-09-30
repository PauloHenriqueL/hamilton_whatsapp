"""
Notificação de valor divergente (D14b, decisões #15/#21).

Quando um crédito casa com um paciente mas o valor difere do combinado, avisa
in-system o terapeuta do paciente e o supervisor dele. WhatsApp é fase 2.
"""
from principais.models import Notificacao


def _texto(trans):
    nome = trans.fk_paciente.nome
    combinado = trans.fk_paciente.vlr_sessao
    return (
        f"Pagamento divergente de {nome}: recebido R$ {trans.valor} "
        f"(combinado R$ {combinado}) em {trans.data:%d/%m/%Y}. "
        f"A nota será emitida pelo valor real recebido."
    )


def notificar_divergencia(trans):
    """Cria notificações para o terapeuta do paciente e seu supervisor.
    Retorna quantas notificações foram criadas."""
    paciente = trans.fk_paciente
    if paciente is None or not trans.valor_divergente:
        return 0
    terapeuta = paciente.fk_terapeuta
    if terapeuta is None:
        return 0

    texto = _texto(trans)
    destinatarios = [terapeuta.fk_associado]
    if terapeuta.fk_supervisor and terapeuta.fk_supervisor.fk_associado_id:
        destinatarios.append(terapeuta.fk_supervisor.fk_associado)

    criadas = 0
    for associado in destinatarios:
        Notificacao.objects.create(destinatario=associado, texto=texto)
        criadas += 1
    return criadas


def notificar_divergencias_do_extrato(extrato):
    """Gera notificações para todas as transações divergentes do extrato."""
    total = 0
    for trans in extrato.transacoes.filter(valor_divergente=True).select_related(
        'fk_paciente__fk_terapeuta__fk_supervisor__fk_associado',
        'fk_paciente__fk_terapeuta__fk_associado',
    ):
        total += notificar_divergencia(trans)
    return total
