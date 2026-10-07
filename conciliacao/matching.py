"""
Motor de conciliação (D14) — casa cada crédito com um paciente por nome + valor.

Estratégia conservadora (recomendação do risco aberto): match exato do nome
normalizado; o resto vai para a fila manual (D15). Quando o nome bate mas o
valor difere do combinado, concilia mesmo assim pelo valor real e levanta a
flag ``valor_divergente`` (decisão #15), que alimenta a notificação (D14b).
"""
from principais.models import PagadorAlternativo, Paciente

from conciliacao.models import TransacaoOFX
from conciliacao.ofx import normalizar_nome
from conciliacao.regras import abaixo_do_minimo


def _indice_pacientes():
    """Dois mapas nome_normalizado → lista de pacientes ativos:
    ``proprio`` (nome do próprio paciente) e ``alternativo`` (pagadores
    alternativos — mãe/pai etc.). O nome próprio tem precedência: os alternativos
    só são consultados quando o nome próprio não casa com ninguém (decisão #7
    estendida)."""
    proprio = {}
    for p in Paciente.objects.filter(is_active=True):
        proprio.setdefault(normalizar_nome(p.nome), []).append(p)

    alternativo = {}
    for pag in PagadorAlternativo.objects.filter(
            fk_paciente__is_active=True).select_related('fk_paciente'):
        alternativo.setdefault(normalizar_nome(pag.nome), []).append(pag.fk_paciente)

    return {'proprio': proprio, 'alternativo': alternativo}


def _desambiguar(candidatos, valor):
    """Resolve a lista de candidatos de um nome. 1 candidato → ele; vários →
    desambigua pelo valor combinado; sem resolução → None (vai p/ fila)."""
    if len(candidatos) == 1:
        return candidatos[0]
    if len(candidatos) > 1:
        por_valor = [p for p in candidatos if p.vlr_sessao == valor]
        if len(por_valor) == 1:
            return por_valor[0]
    return None


def conciliar_transacao(trans, indice=None):
    """Concilia uma transação. Retorna o paciente casado (ou None). Salva o
    status/flag na própria transação.

    Primeiro tenta o nome do próprio paciente; só se nenhum paciente tiver aquele
    nome, tenta os pagadores alternativos. Em ambos, empate é resolvido pelo valor
    e, se persistir, a transação vai para a fila manual."""
    if indice is None:
        indice = _indice_pacientes()

    chave = trans.nome_normalizado
    # 1) Nome do próprio paciente (precedência).
    escolhido = _desambiguar(indice['proprio'].get(chave, []), trans.valor)
    # 2) Fallback: pagadores alternativos — só quando o nome próprio não casou
    #    com NINGUÉM (lista vazia). Se o nome próprio tinha candidatos mas ficou
    #    ambíguo, respeita a fila manual e não mistura com os alternativos.
    if escolhido is None and not indice['proprio'].get(chave):
        escolhido = _desambiguar(indice['alternativo'].get(chave, []), trans.valor)

    if escolhido is None:
        trans.fk_paciente = None
        trans.status_conciliacao = TransacaoOFX.NAO_IDENTIFICADO
        trans.valor_divergente = False
    else:
        trans.fk_paciente = escolhido
        trans.status_conciliacao = TransacaoOFX.CONCILIADO
        # Concilia sempre pelo valor real (decisão #3). A flag/alerta agora é só
        # quando o pagamento fica ABAIXO do mínimo global (decisão #15 revisada).
        trans.valor_divergente = abaixo_do_minimo(escolhido, trans.valor)

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
