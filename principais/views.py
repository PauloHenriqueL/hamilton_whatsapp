"""
Views da app ``principais``.

Nesta fase (Bloco A / D4) são só o roteador de papel e telas *placeholder* que
provam o shell: login, redirect por papel e o gate de gestor. Cada placeholder
será substituído pela sua demanda (D7 pacientes, D8 encaminhamento, D9
terapeutas, D11 portal do terapeuta).
"""
from datetime import time, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Exists, OuterRef, Q, Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.generic import (
    CreateView, DetailView, ListView, TemplateView, UpdateView,
)

from principais.forms import HorarioDisponivelFormSet, PacienteFilterForm, PacienteForm
from principais.mixins import (
    StaffRequiredMixin, TerapeutaRequiredMixin, terapeuta_em_foco,
)
from principais.models import Abordagem, HorarioDisponivel, Paciente, Terapeuta


# ---- Telas de gestão (gate is_staff) ----
class ControlePacientesView(StaffRequiredMixin, ListView):
    """Controle de Pacientes (D7). Portado do Hamilton e podado: só os 2 KPIs
    do 2.0 (novos 30d + capacidade), sem colunas de consulta/avaliação/stripe;
    'dias sem atividade' passa a ser dias desde ``created_at`` (não há mais
    Consulta). Colunas 'pago no mês' e 'situação fiscal' entram como placeholder
    até a conciliação (D15)."""
    model = Paciente
    template_name = 'pacientes/controle_novos_pacientes.html'
    context_object_name = 'pacientes'
    paginate_by = 20

    def get_queryset(self):
        from conciliacao.models import TransacaoOFX  # import tardio (evita ciclo)
        pago_subq = TransacaoOFX.objects.filter(
            fk_paciente=OuterRef('pk'), status_conciliacao=TransacaoOFX.CONCILIADO,
        )
        qs = (
            Paciente.objects.select_related('fk_terapeuta__fk_associado')
            .annotate(tem_pagamento=Exists(pago_subq))
        )
        self.filter_form = PacienteFilterForm(self.request.GET)
        if self.filter_form.is_valid():
            d = self.filter_form.cleaned_data
            if d.get('data_inicial'):
                qs = qs.filter(created_at__date__gte=d['data_inicial'])
            if d.get('data_final'):
                qs = qs.filter(created_at__date__lte=d['data_final'])
            situacao = d.get('situacao')
            if situacao == 'ativos':
                qs = qs.filter(is_active=True)
            elif situacao == 'inativos':
                qs = qs.filter(is_active=False)
            elif situacao == 'aguardando':
                qs = qs.filter(is_active=True, fk_terapeuta__isnull=True)

        termo = self.request.GET.get('q')
        if termo:
            qs = qs.filter(
                Q(nome__icontains=termo) |
                Q(fk_terapeuta__fk_associado__nome__icontains=termo)
            )
        if self.request.GET.get('novos') == '30d':
            qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=30))
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['filter_form'] = self.filter_form
        trinta = timezone.now() - timedelta(days=30)

        # KPI 1 — novos nos últimos 30 dias.
        ctx['kpi_total_novos_30d'] = Paciente.objects.filter(created_at__gte=trinta).count()

        # KPI 2 — capacidade: pacientes ativos × soma do pacientes_max (ativos).
        ctx['kpi_capacidade_numerador'] = Paciente.objects.filter(is_active=True).count()
        ctx['kpi_capacidade_denominador'] = (
            Terapeuta.objects.filter(is_active=True)
            .aggregate(total=Sum('pacientes_max'))['total'] or 0
        )

        ctx['terapeutas'] = Terapeuta.objects.select_related('fk_associado').filter(is_active=True)
        ctx['current_search'] = self.request.GET.get('q', '')
        params = self.request.GET.copy()
        params.pop('page', None)
        ctx['filter_params'] = params.urlencode()
        return ctx


@login_required
@require_http_methods(["POST"])
def notificacao_marcar_lida(request, pk):
    """Marca uma notificação do próprio usuário como lida (D14b)."""
    from principais.models import Associado, Notificacao
    associado = Associado.objects.filter(usuario=request.user).first()
    if associado:
        Notificacao.objects.filter(pk=pk, destinatario=associado).update(lida=True)
    return redirect(request.META.get('HTTP_REFERER') or 'dashboard')


@login_required
@require_http_methods(["POST"])
def supervisao_visualizar(request, pk):
    """Entra no modo 'ver como' um supervisionado (D11b)."""
    from principais.supervisao import SESSION_KEY, _meu_terapeuta, supervisionados_de
    meu = _meu_terapeuta(request)
    alvo = supervisionados_de(meu).filter(pk=pk).first()
    if not alvo:
        messages.error(request, 'Supervisionado inválido.')
        return redirect(request.META.get('HTTP_REFERER') or 'meus-horarios')
    request.session[SESSION_KEY] = alvo.pk_terapeuta
    messages.info(request, f'Vendo como {alvo.fk_associado.nome} (somente leitura).')
    return redirect(request.POST.get('next') or 'meus-pacientes')


@login_required
@require_http_methods(["POST"])
def supervisao_voltar(request):
    """Volta à própria visualização (D11b)."""
    from principais.supervisao import SESSION_KEY
    request.session.pop(SESSION_KEY, None)
    messages.info(request, 'De volta à sua visualização.')
    return redirect(request.POST.get('next') or 'meus-pacientes')


@method_decorator(staff_member_required, name='dispatch')
class EncaminhamentoView(TemplateView):
    """Encaminhamento (D8). Portado quase igual do Hamilton: filtra terapeutas
    por nome/abordagem/dia/hora e calcula os slots de 1h livres (disponíveis
    menos os ocupados por dia_semana_padrao/hora_padrao). 'Aguardando' passa a
    ser ``fk_terapeuta IS NULL`` (substitui o sentinela/id 73)."""
    template_name = 'pacientes/encaminhamento.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['abordagens'] = Abordagem.objects.all().order_by('abordagem')
        # Aguardando encaminhamento = sem terapeuta (decisão do 2.0).
        context['pacientes_aguardando'] = Paciente.objects.filter(
            fk_terapeuta__isnull=True, is_active=True
        ).order_by('created_at')

        dias = self.request.GET.getlist('dia_semana')
        horas = self.request.GET.getlist('hora')
        abordagens = self.request.GET.getlist('abordagem')
        nome_terapeuta = self.request.GET.get('nome_terapeuta', '').strip()

        if dias or horas or abordagens or nome_terapeuta:
            context['terapeutas_resultado'] = self.buscar_terapeutas(
                dias, horas, abordagens, nome_terapeuta
            )
            context['total_encontrados'] = len(context['terapeutas_resultado'])
            context['filtros_aplicados'] = True
        else:
            context['filtros_aplicados'] = False

        context['dias_selecionados'] = dias
        context['horas_selecionadas'] = horas
        context['abordagens_selecionadas'] = abordagens
        context['nome_terapeuta'] = nome_terapeuta
        context['horas_disponiveis'] = list(range(7, 22))
        return context

    def buscar_terapeutas(self, dias, horas_selecionadas, abordagens, nome_terapeuta=''):
        terapeutas_qs = Terapeuta.objects.filter(is_active=True).select_related(
            'fk_associado', 'fk_abordagem'
        )
        if nome_terapeuta:
            terapeutas_qs = terapeutas_qs.filter(fk_associado__nome__icontains=nome_terapeuta)
        if abordagens and 'todas' not in abordagens:
            terapeutas_qs = terapeutas_qs.filter(fk_abordagem_id__in=abordagens)

        horarios_qs = HorarioDisponivel.objects.filter(
            fk_terapeuta__in=terapeutas_qs
        ).select_related('fk_terapeuta', 'fk_terapeuta__fk_associado', 'fk_terapeuta__fk_abordagem')
        if dias and 'todos' not in dias:
            horarios_qs = horarios_qs.filter(dia_semana__in=[int(d) for d in dias])

        # Slots já ocupados: (terapeuta_id, dia_semana, hora_padrao).
        slots_ocupados = set(
            Paciente.objects.filter(
                is_active=True, dia_semana_padrao__isnull=False, hora_padrao__isnull=False
            ).values_list('fk_terapeuta_id', 'dia_semana_padrao', 'hora_padrao')
        )

        horas_filtro = None
        if horas_selecionadas and 'todas' not in horas_selecionadas:
            horas_filtro = [int(h) for h in horas_selecionadas]

        results = []
        for horario in horarios_qs:
            terapeuta = horario.fk_terapeuta
            slot_inicio = horario.hora_inicio
            bloco_fim = horario.hora_fim
            while slot_inicio < bloco_fim:
                slot_fim = time(slot_inicio.hour + 1, slot_inicio.minute)
                if (terapeuta.pk_terapeuta, horario.dia_semana, slot_inicio) in slots_ocupados:
                    slot_inicio = slot_fim
                    continue
                if horas_filtro and slot_inicio.hour not in horas_filtro:
                    slot_inicio = slot_fim
                    continue
                results.append({
                    'pk_terapeuta': terapeuta.pk_terapeuta,
                    'terapeuta': terapeuta.fk_associado.nome,
                    'telefone': terapeuta.fk_associado.telefone,
                    'email': terapeuta.fk_associado.email,
                    'abordagem': terapeuta.fk_abordagem.abordagem if terapeuta.fk_abordagem else '—',
                    'pacientes_max': terapeuta.pacientes_max,
                    'observacao': terapeuta.observacao,
                    'dia_semana': horario.dia_semana,
                    'hora_inicio': slot_inicio,
                    'hora_fim': slot_fim,
                })
                slot_inicio = slot_fim

        terapeutas_ids = {r['pk_terapeuta'] for r in results}
        contagem = dict(
            Paciente.objects.filter(fk_terapeuta_id__in=terapeutas_ids, is_active=True)
            .values_list('fk_terapeuta_id')
            .annotate(total=Count('pk_paciente'))
            .values_list('fk_terapeuta_id', 'total')
        )
        for r in results:
            r['qtd_pacientes'] = contagem.get(r['pk_terapeuta'], 0)
        results.sort(key=lambda r: (r['terapeuta'], r['dia_semana'], r['hora_inicio']))
        return self._agrupar_terapeutas(results)

    def _agrupar_terapeutas(self, results):
        dias_nome = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sáb', 6: 'Dom'}
        agrupado = {}
        for row in results:
            tid = row['pk_terapeuta']
            if tid not in agrupado:
                vagas = row['pacientes_max'] - row['qtd_pacientes'] if row['pacientes_max'] else None
                cor = 'secondary' if vagas is None else (
                    'success' if vagas > 2 else ('warning' if vagas > 0 else 'danger')
                )
                agrupado[tid] = {**row, 'nome': row['terapeuta'], 'vagas': vagas,
                                 'cor_vaga': cor, 'horarios': []}
            if row['dia_semana'] is not None:
                agrupado[tid]['horarios'].append({
                    'dia': dias_nome.get(row['dia_semana'], '?'),
                    'inicio': row['hora_inicio'].strftime('%H:%M'),
                    'fim': row['hora_fim'].strftime('%H:%M'),
                })
        return list(agrupado.values())


@login_required
@staff_member_required
@require_http_methods(["POST"])
def alocar_terapeuta_view(request):
    """Aloca um terapeuta a um paciente aguardando (D8). Portado do Hamilton."""
    paciente_id = request.POST.get('paciente_id')
    terapeuta_id = request.POST.get('terapeuta_id')
    fallback = request.META.get('HTTP_REFERER') or 'controle-pacientes'

    if not paciente_id or not terapeuta_id:
        messages.error(request, "Dados incompletos para alocação.")
        return redirect(fallback)
    try:
        paciente = Paciente.objects.get(pk_paciente=paciente_id)
        terapeuta = Terapeuta.objects.get(pk_terapeuta=terapeuta_id)
        # Trava dupla (decisão B): nº de pacientes E horas livres. Vale o que
        # estourar primeiro. Alocar +1 paciente consome +1h.
        ativos = Paciente.objects.filter(fk_terapeuta=terapeuta, is_active=True).count()
        if terapeuta.pacientes_max and ativos >= terapeuta.pacientes_max:
            messages.warning(
                request,
                f"O terapeuta {terapeuta.fk_associado.nome} já atingiu o máximo de pacientes."
            )
            return redirect(fallback)
        if terapeuta.horas_livres < Decimal('1'):
            messages.warning(
                request,
                f"O terapeuta {terapeuta.fk_associado.nome} não tem horas livres "
                f"({terapeuta.horas_ocupadas}/{terapeuta.horas_total}h)."
            )
            return redirect(fallback)
        paciente.fk_terapeuta = terapeuta
        if not paciente.is_active:
            paciente.is_active = True
        paciente.save()
        messages.success(
            request,
            f"Paciente {paciente.nome} alocado para {terapeuta.fk_associado.nome}."
        )
    except Paciente.DoesNotExist:
        messages.error(request, "Paciente não encontrado.")
    except Terapeuta.DoesNotExist:
        messages.error(request, "Terapeuta não encontrado.")
    return redirect(fallback)


class PacienteCreateView(StaffRequiredMixin, CreateView):
    model = Paciente
    form_class = PacienteForm
    template_name = 'pacientes/paciente_form.html'
    success_url = reverse_lazy('controle-pacientes')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Cadastrar Novo Paciente'
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Paciente cadastrado com sucesso!')
        return super().form_valid(form)


class PacienteUpdateView(StaffRequiredMixin, UpdateView):
    model = Paciente
    form_class = PacienteForm
    template_name = 'pacientes/paciente_form.html'
    context_object_name = 'paciente'

    def get_queryset(self):
        return super().get_queryset().select_related('fk_terapeuta__fk_associado')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = f'Editar Paciente: {self.object.nome}'
        return ctx

    def get_success_url(self):
        return reverse_lazy('paciente-detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, f"Dados de '{self.object.nome}' atualizados.")
        return super().form_valid(form)


class PacienteDetailView(StaffRequiredMixin, DetailView):
    model = Paciente
    template_name = 'pacientes/paciente_detail.html'
    context_object_name = 'paciente'

    def get_queryset(self):
        return super().get_queryset().select_related('fk_terapeuta__fk_associado')


class PacienteDuplicarView(StaffRequiredMixin, View):
    """Duplica um paciente e leva para a edição do novo."""
    http_method_names = ['post']

    def post(self, request, pk, *args, **kwargs):
        original = get_object_or_404(Paciente, pk=pk)
        novo = get_object_or_404(Paciente, pk=pk)
        novo.pk = None
        novo.nome = f'Cópia de {original.nome}'
        novo.cpf = None  # CPF é único; preenchido na edição.
        novo._state.adding = True
        novo.save()
        messages.info(request, f"Paciente duplicado a partir de '{original.nome}'. Revise e salve.")
        return redirect('paciente-update', pk=novo.pk)


class PacienteDeleteView(StaffRequiredMixin, View):
    """Exclusão lógica: marca o paciente como inativo."""
    http_method_names = ['post']

    def post(self, request, pk, *args, **kwargs):
        paciente = get_object_or_404(Paciente, pk=pk)
        paciente.is_active = False
        paciente.save(update_fields=['is_active', 'updated_at'])
        messages.success(request, f"Paciente '{paciente.nome}' inativado.")
        return redirect('controle-pacientes')


# ---- Portal do terapeuta (não-staff) — D11 ----
def _render_horarios(view, terapeuta, is_view_as, titulo, formset=None):
    contexto = {
        'terapeuta_foco': terapeuta,
        'is_view_as': is_view_as,
        'titulo': titulo,
        'horario_formset': formset or HorarioDisponivelFormSet(
            instance=terapeuta, prefix='horarios'
        ),
    }
    return view.render_to_response(contexto)


class MeusHorariosView(TerapeutaRequiredMixin, TemplateView):
    """O terapeuta logado edita os próprios HorarioDisponivel (insumo do
    Encaminhamento). Em modo supervisão (D11b) fica somente-leitura."""
    template_name = 'horarios/meus_horarios.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.terapeuta, self.is_view_as = terapeuta_em_foco(request)
            if request.user.is_staff and self.terapeuta is None:
                # Gestor sem perfil de terapeuta não tem "meus horários".
                return redirect('controle-terapeutas')
            if self.terapeuta is None:
                messages.error(request, 'Seu usuário não está vinculado a um terapeuta.')
                return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return _render_horarios(self, self.terapeuta, self.is_view_as,
                                'Meus Horários Disponíveis')

    def post(self, request, *args, **kwargs):
        if self.is_view_as:
            messages.error(request, 'Modo supervisão é somente-leitura.')
            return redirect('meus-horarios')
        formset = HorarioDisponivelFormSet(
            request.POST, instance=self.terapeuta, prefix='horarios'
        )
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Horários atualizados com sucesso!')
            return redirect('meus-horarios')
        messages.error(request, 'Corrija os erros abaixo.')
        return _render_horarios(self, self.terapeuta, self.is_view_as,
                                'Meus Horários Disponíveis', formset)


class MeusPacientesView(TerapeutaRequiredMixin, ListView):
    """Lista (somente leitura) dos pacientes vinculados ao terapeuta em foco."""
    template_name = 'pacientes/meus_pacientes.html'
    context_object_name = 'pacientes'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.terapeuta, self.is_view_as = terapeuta_em_foco(request)
            if self.terapeuta is None:
                if request.user.is_staff:
                    return redirect('controle-terapeutas')
                messages.error(request, 'Seu usuário não está vinculado a um terapeuta.')
                return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Paciente.objects.filter(
            fk_terapeuta=self.terapeuta, is_active=True
        ).order_by('nome')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['terapeuta_foco'] = self.terapeuta
        ctx['is_view_as'] = self.is_view_as
        return ctx


class GerenciarHorariosView(StaffRequiredMixin, TemplateView):
    """O gestor edita os horários de qualquer terapeuta (D11)."""
    template_name = 'horarios/meus_horarios.html'

    def dispatch(self, request, *args, **kwargs):
        self.terapeuta = get_object_or_404(Terapeuta, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        titulo = f'Horários de {self.terapeuta.fk_associado.nome}'
        return _render_horarios(self, self.terapeuta, False, titulo)

    def post(self, request, *args, **kwargs):
        formset = HorarioDisponivelFormSet(
            request.POST, instance=self.terapeuta, prefix='horarios'
        )
        titulo = f'Horários de {self.terapeuta.fk_associado.nome}'
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Horários atualizados com sucesso!')
            return redirect('gerenciar-horarios', pk=self.terapeuta.pk_terapeuta)
        messages.error(request, 'Corrija os erros abaixo.')
        return _render_horarios(self, self.terapeuta, False, titulo, formset)
