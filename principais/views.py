"""
Views da app ``principais``.

Nesta fase (Bloco A / D4) são só o roteador de papel e telas *placeholder* que
provam o shell: login, redirect por papel e o gate de gestor. Cada placeholder
será substituído pela sua demanda (D7 pacientes, D8 encaminhamento, D9
terapeutas, D11 portal do terapeuta).
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView

from principais.mixins import StaffRequiredMixin, TerapeutaRequiredMixin


class HomeView(LoginRequiredMixin, TemplateView):
    """Rota ``/`` — despacha por papel (decisão #1/#16):
    gestor cai no dashboard; terapeuta é levado para "Meus Horários"."""

    template_name = 'placeholder.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_staff:
            return redirect('meus-horarios')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Dashboard'
        ctx['descricao'] = (
            'Placeholder do dashboard (gestor). Os 2 KPIs — capacidade da '
            'equipe e pendências de conciliação — chegam na D20.'
        )
        return ctx


class _PlaceholderView(TemplateView):
    """Base de tela placeholder que estende o ``base.html`` do Hamilton."""
    template_name = 'placeholder.html'
    titulo = 'Em breve'
    descricao = ''

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = self.titulo
        ctx['descricao'] = self.descricao
        return ctx


# ---- Telas de gestão (gate is_staff) — substituídas pelas demandas da Fase 1 ----
class PacientesPlaceholderView(StaffRequiredMixin, _PlaceholderView):
    titulo = 'Controle de Pacientes'
    descricao = 'Placeholder — tela real na D7.'


class TerapeutasPlaceholderView(StaffRequiredMixin, _PlaceholderView):
    titulo = 'Controle de Terapeutas'
    descricao = 'Placeholder — tela real na D9.'


class EncaminhamentoPlaceholderView(StaffRequiredMixin, _PlaceholderView):
    titulo = 'Encaminhamento'
    descricao = 'Placeholder — tela real na D8.'


class ConciliacaoPlaceholderView(StaffRequiredMixin, _PlaceholderView):
    titulo = 'Conciliação / OFX'
    descricao = 'Placeholder — importação e fila de pendências na Fase 2 (D13–D15).'


class NotasPlaceholderView(StaffRequiredMixin, _PlaceholderView):
    titulo = 'Notas Fiscais'
    descricao = 'Placeholder — painel de notas na Fase 3 (D18).'


# ---- Portal do terapeuta (não-staff) — substituído pela D11/D11b ----
class MeusHorariosPlaceholderView(TerapeutaRequiredMixin, _PlaceholderView):
    titulo = 'Meus Horários'
    descricao = 'Placeholder — edição de horários na D11.'


class MeusPacientesPlaceholderView(TerapeutaRequiredMixin, _PlaceholderView):
    titulo = 'Meus Pacientes'
    descricao = 'Placeholder — lista (leitura) na D11.'
