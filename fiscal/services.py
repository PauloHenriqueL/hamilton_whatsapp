"""
Fechamento do mês → geração de notas (D17).

Fluxo manual (decisão #14): o gestor entra ~dia 15 e fecha o mês anterior,
gerando uma NotaFiscal PENDENTE por paciente pago. Valor = soma real das
TransacaoOFX conciliadas do paciente no mês (decisão #3). Pula:
  - isento: paciente com vlr_sessao 0 (decisão #5) — na prática nem paga;
  - sem CPF/sem pagador: não emite, fica a flag na tela do paciente (decisão #4).
"""
from dataclasses import dataclass, field

from dateutil.relativedelta import relativedelta
from django.db.models import Sum

from conciliacao.models import TransacaoOFX
from fiscal.models import NotaFiscal


def competencia_mes_anterior(hoje):
    """Primeiro dia do mês anterior a ``hoje`` (competência padrão, decisão #2)."""
    return (hoje.replace(day=1) - relativedelta(months=1))


@dataclass
class ResultadoFechamento:
    competencia: object
    criadas: int = 0
    ja_existiam: int = 0
    isentos: int = 0
    sem_cpf: list = field(default_factory=list)   # nomes de pacientes pagos sem CPF
    total_valor: object = 0


def gerar_notas_do_mes(competencia):
    """Gera as NotaFiscal PENDENTE da competência (primeiro dia do mês).
    Retorna um ``ResultadoFechamento``."""
    inicio = competencia.replace(day=1)
    fim = (inicio + relativedelta(months=1)) - relativedelta(days=1)

    # Soma dos créditos conciliados por paciente no mês.
    somas = (
        TransacaoOFX.objects
        .filter(status_conciliacao=TransacaoOFX.CONCILIADO,
                fk_paciente__isnull=False, data__range=[inicio, fim])
        .values('fk_paciente')
        .annotate(total=Sum('valor'))
    )

    res = ResultadoFechamento(competencia=inicio, total_valor=0)
    from principais.models import Paciente

    for linha in somas:
        paciente = Paciente.objects.get(pk=linha['fk_paciente'])
        valor = linha['total'] or 0

        # Isento: valor combinado 0 (decisão #5).
        if paciente.vlr_sessao == 0 or valor == 0:
            res.isentos += 1
            continue
        # Sem CPF → não emite; fica a flag na tela do paciente (decisão #4).
        if not paciente.tem_cpf:
            res.sem_cpf.append(paciente.nome)
            continue

        nota, criada = NotaFiscal.objects.get_or_create(
            fk_paciente=paciente, mes_competencia=inicio,
            defaults={'valor': valor, 'status_nfs': NotaFiscal.PENDENTE},
        )
        if criada:
            res.criadas += 1
            res.total_valor += valor
        else:
            res.ja_existiam += 1
            # Atualiza o valor só se a nota ainda não foi emitida.
            if nota.status_nfs in (NotaFiscal.PENDENTE, NotaFiscal.ERRO) and nota.valor != valor:
                nota.valor = valor
                nota.save(update_fields=['valor', 'updated_at'])
    return res
