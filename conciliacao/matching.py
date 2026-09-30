"""
Motor de conciliação (D14) — casa cada crédito com um paciente por nome + valor.

Estratégia conservadora (recomendação do risco aberto): match exato do nome
normalizado; o resto vai para a fila manual (D15). Quando o nome bate mas o
valor difere do combinado, concilia mesmo assim pelo valor real e levanta a
flag ``valor_divergente`` (decisão #15), que alimenta a notificação (D14b).
"""
from principais.models import Paciente

from conciliacao.models import TransacaoOFX
from conciliacao.ofx import normalizar_nome


def _indice_pacientes():
    """Mapa nome_normalizado → lista de pacientes ativos com aquele nome."""
    indice = {}
    for p in Paciente.objects.filter(is_active=True):
        indice.setdefault(normalizar_nome(p.nome), []).append(p)
    return indice


def conciliar_transacao(trans, indice=None):
    """Concilia uma transação. Retorna o paciente casado (ou None). Salva o
    status/flag na própria transação."""
    if indice is None:
        indice = _indice_pacientes()

    candidatos = indice.get(trans.nome_normalizado, [])

    escolhido = None
    if len(candidatos) == 1:
        escolhido = candidatos[0]
    elif len(candidatos) > 1:
        # Desambigua pelo valor combinado; se ainda ficar ambíguo, vai p/ fila.
        por_valor = [p for p in candidatos if p.vlr_sessao == trans.valor]
        if len(por_valor) == 1:
            escolhido = por_valor[0]

    if escolhido is None:
        trans.fk_paciente = None
        trans.status_conciliacao = TransacaoOFX.NAO_IDENTIFICADO
        trans.valor_divergente = False
    else:
        trans.fk_paciente = escolhido
        trans.status_conciliacao = TransacaoOFX.CONCILIADO
        # Valor real diverge do combinado? Concilia mesmo assim + flag (decisão #15).
        trans.valor_divergente = escolhido.vlr_sessao != trans.valor

    trans.save(update_fields=['fk_paciente', 'status_conciliacao', 'valor_divergente'])
    return escolhido


def conciliar_extrato(extrato):
    """Concilia todas as transações de um extrato. Retorna (conciliadas,
    divergentes, nao_identificadas)."""
    indice = _indice_pacientes()
    conciliadas = divergentes = nao_id = 0
    for trans in extrato.transacoes.all():
        escolhido = conciliar_transacao(trans, indice)
        if escolhido is None:
            nao_id += 1
        else:
            conciliadas += 1
            if trans.valor_divergente:
                divergentes += 1
    return conciliadas, divergentes, nao_id
