"""Dashboard do gestor (D20) — os 2 KPIs do 2.0 (decisão #18)."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import redirect
from django.views.generic import TemplateView

from conciliacao.models import TransacaoOFX
from principais.models import Paciente, Terapeuta


class DashboardView(LoginRequiredMixin, TemplateView):
    """Home do gestor. Terapeuta é redirecionado para 'Meus Horários'."""
    template_name = 'dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_staff:
            return redirect('meus-horarios')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # KPI 1 — Capacidade da equipe: pacientes ativos × soma do pacientes_max
        # dos terapeutas ativos (ativos / máximo combinado).
        ctx['kpi_pacientes_ativos'] = Paciente.objects.filter(is_active=True).count()
        ctx['kpi_capacidade_total'] = (
            Terapeuta.objects.filter(is_active=True)
            .aggregate(total=Sum('pacientes_max'))['total'] or 0
        )

        # KPI 2 — Pendências de conciliação em aberto (créditos não identificados).
        ctx['kpi_pendencias_conciliacao'] = TransacaoOFX.objects.filter(
            status_conciliacao=TransacaoOFX.NAO_IDENTIFICADO
        ).count()

        # Painel de atividades & substitutos (quem dá / quem é apto).
        from principais.views_controle_terapeutas import _painel_substitutos
        ctx['atividades'] = _painel_substitutos()
        return ctx
