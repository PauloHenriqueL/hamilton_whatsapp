"""Views de conciliação: importação de OFX (D13) e painel/fila (D15)."""
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

from principais.mixins import StaffRequiredMixin
from principais.models import Paciente

from conciliacao import ofx as ofx_parser
from conciliacao.matching import conciliar_extrato, conciliar_transacao
from conciliacao.models import ExtratoOFX, TransacaoOFX
from conciliacao.notificacoes import notificar_divergencias_do_extrato


@method_decorator(staff_member_required, name='dispatch')
class ImportarOFXView(TemplateView):
    """Upload do OFX → grava créditos sem duplicar (hash do arquivo + fitid),
    concilia e notifica divergências (D13/D14/D14b)."""
    template_name = 'conciliacao/importar.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['extratos'] = ExtratoOFX.objects.all()[:20]
        return ctx

    def post(self, request, *args, **kwargs):
        arquivo = request.FILES.get('arquivo')
        if not arquivo:
            messages.error(request, 'Selecione um arquivo OFX.')
            return redirect('conciliacao-importar')

        conteudo = arquivo.read()
        hash_arq = ofx_parser.hash_conteudo(conteudo)

        if ExtratoOFX.objects.filter(hash_arquivo=hash_arq).exists():
            messages.warning(request, 'Este extrato já foi importado (idempotência).')
            return redirect('conciliacao-importar')

        texto = ofx_parser.decodificar(conteudo)
        creditos, conta = ofx_parser.parse_creditos(texto)
        if not creditos:
            messages.error(request, 'Nenhum crédito encontrado no arquivo.')
            return redirect('conciliacao-importar')

        datas = [c['data'] for c in creditos if c['data']]
        with transaction.atomic():
            extrato = ExtratoOFX.objects.create(
                arquivo_nome=arquivo.name, hash_arquivo=hash_arq, conta=conta,
                data_inicio=min(datas) if datas else None,
                data_fim=max(datas) if datas else None,
            )
            novas = 0
            for c in creditos:
                # Idempotência por fitid: nunca duplica um crédito já visto.
                if TransacaoOFX.objects.filter(fitid=c['fitid']).exists():
                    continue
                TransacaoOFX.objects.create(fk_extrato=extrato, **c)
                novas += 1

        conciliadas, divergentes, nao_id = conciliar_extrato(extrato)
        notificadas = notificar_divergencias_do_extrato(extrato)

        messages.success(
            request,
            f"Importado: {novas} crédito(s). Conciliados: {conciliadas} "
            f"({divergentes} divergente(s)); não identificados: {nao_id}. "
            f"Notificações enviadas: {notificadas}."
        )
        return redirect('conciliacao-painel')


@method_decorator(staff_member_required, name='dispatch')
class PainelConciliacaoView(TemplateView):
    """Fila de pendências (não identificados) + conciliados (D15)."""
    template_name = 'conciliacao/painel.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['pendentes'] = (
            TransacaoOFX.objects.filter(status_conciliacao=TransacaoOFX.NAO_IDENTIFICADO)
            .select_related('fk_extrato')
        )
        ctx['conciliados'] = (
            TransacaoOFX.objects.filter(status_conciliacao=TransacaoOFX.CONCILIADO)
            .select_related('fk_paciente')[:200]
        )
        ctx['pacientes'] = Paciente.objects.filter(is_active=True).order_by('nome')
        return ctx


@login_required
@staff_member_required
@require_http_methods(["POST"])
def associar_paciente_view(request, pk):
    """Associa manualmente um crédito não identificado a um paciente (D15)."""
    trans = get_object_or_404(TransacaoOFX, pk=pk)
    paciente_id = request.POST.get('paciente_id')
    if not paciente_id:
        messages.error(request, 'Selecione um paciente.')
        return redirect('conciliacao-painel')
    paciente = get_object_or_404(Paciente, pk=paciente_id)
    trans.fk_paciente = paciente
    trans.status_conciliacao = TransacaoOFX.CONCILIADO
    trans.valor_divergente = paciente.vlr_sessao != trans.valor
    trans.save(update_fields=['fk_paciente', 'status_conciliacao', 'valor_divergente'])
    # Se a associação manual revelou divergência, notifica (D14b).
    if trans.valor_divergente:
        from conciliacao.notificacoes import notificar_divergencia
        notificar_divergencia(trans)
    messages.success(request, f"Crédito associado a {paciente.nome}.")
    return redirect('conciliacao-painel')
