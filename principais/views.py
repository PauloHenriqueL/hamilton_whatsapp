"""
Views da app ``principais``.

Nesta fase (Bloco A / D4) são só o roteador de papel e telas *placeholder* que
provam o shell: login, redirect por papel e o gate de gestor. Cada placeholder
será substituído pela sua demanda (D7 pacientes, D8 encaminhamento, D9
terapeutas, D11 portal do terapeuta).
"""
import json
from datetime import time, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.generic import (
    CreateView, DetailView, ListView, TemplateView, UpdateView,
)

from principais.forms import PacienteFilterForm, PacienteForm, PagadorAlternativoFormSet
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
        from datetime import date
        from conciliacao.models import TransacaoOFX  # import tardio (evita ciclo)
        pago_subq = TransacaoOFX.objects.filter(
            fk_paciente=OuterRef('pk'), status_conciliacao=TransacaoOFX.CONCILIADO,
        )
        hoje = date.today()
        inicio_mes = hoje.replace(day=1)
        pago_mes_subq = pago_subq.filter(data__gte=inicio_mes, data__lte=hoje)
        qs = (
            Paciente.objects.select_related('fk_terapeuta__fk_associado')
            .annotate(tem_pagamento=Exists(pago_subq), pago_mes=Exists(pago_mes_subq))
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
        # Marca atraso por paciente da página (expectativa pela data do Pix).
        from conciliacao.regras import esta_em_atraso
        for p in ctx.get('pacientes', []):
            p.em_atraso = esta_em_atraso(p, p.pago_mes)
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
def notificacoes_marcar_todas_lidas(request):
    """Marca todas as notificações não lidas do usuário como lidas (D14b)."""
    from principais.models import Associado, Notificacao
    associado = Associado.objects.filter(usuario=request.user).first()
    if associado:
        Notificacao.objects.filter(destinatario=associado, lida=False).update(lida=True)
    return redirect(request.POST.get('next') or request.META.get('HTTP_REFERER') or 'dashboard')


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

        # Slots já ocupados: (terapeuta_id, dia_semana, hora) das sessões semanais.
        from principais.models import SessaoSemanal
        slots_ocupados = set(
            SessaoSemanal.objects.filter(fk_paciente__is_active=True)
            .values_list('fk_paciente__fk_terapeuta_id', 'dia_semana', 'hora_inicio')
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
        # Teto de nº de pacientes (pacientes_max). O teto de horas é aplicado ao
        # ADICIONAR sessões no calendário (cada sessão = 1h), não ao vincular.
        ativos = Paciente.objects.filter(fk_terapeuta=terapeuta, is_active=True).count()
        if terapeuta.pacientes_max and ativos >= terapeuta.pacientes_max:
            messages.warning(
                request,
                f"O terapeuta {terapeuta.fk_associado.nome} já atingiu o máximo de pacientes."
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
        if 'pagadores' not in ctx:
            ctx['pagadores'] = PagadorAlternativoFormSet(
                self.request.POST or None, instance=self.object)
        return ctx

    def form_valid(self, form):
        self.object = form.save()
        pagadores = PagadorAlternativoFormSet(self.request.POST, instance=self.object)
        if not pagadores.is_valid():
            return self.render_to_response(self.get_context_data(form=form, pagadores=pagadores))
        pagadores.save()
        messages.success(self.request, 'Paciente cadastrado com sucesso!')
        return redirect(self.get_success_url())


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
        if 'pagadores' not in ctx:
            ctx['pagadores'] = PagadorAlternativoFormSet(
                self.request.POST or None, instance=self.object)
        return ctx

    def get_success_url(self):
        return reverse_lazy('paciente-detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        self.object = form.save()
        pagadores = PagadorAlternativoFormSet(self.request.POST, instance=self.object)
        if not pagadores.is_valid():
            return self.render_to_response(self.get_context_data(form=form, pagadores=pagadores))
        pagadores.save()
        messages.success(self.request, f"Dados de '{self.object.nome}' atualizados.")
        return redirect(self.get_success_url())


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
def _hhmm(t):
    return t.strftime('%H:%M')


def _horarios_contexto(terapeuta, is_view_as, titulo, can_edit):
    """Dados do calendário semanal (blocos, pacientes, tags e capacidade)."""
    blocos = [
        {
            'id': h.pk, 'dia': h.dia_semana,
            'inicio': _hhmm(h.hora_inicio), 'fim': _hhmm(h.hora_fim),
            'tag_id': h.fk_tag_id,
            'tag_nome': h.fk_tag.nome if h.fk_tag_id else None,
        }
        for h in terapeuta.horarios.select_related('fk_tag').all()
    ]
    from principais.models import SessaoSemanal
    pacientes = []
    sessoes = SessaoSemanal.objects.filter(
        fk_paciente__fk_terapeuta=terapeuta, fk_paciente__is_active=True
    ).select_related('fk_paciente')
    for s in sessoes:
        fim = time((s.hora_inicio.hour + 1) % 24, s.hora_inicio.minute)
        pacientes.append({
            'sessao_id': s.pk, 'id': s.fk_paciente_id, 'nome': s.fk_paciente.nome,
            'dia': s.dia_semana, 'inicio': _hhmm(s.hora_inicio), 'fim': _hhmm(fim),
        })
    tags = [
        {'id': t.pk_tag, 'nome': t.nome,
         'horas': float(t.horas_consumidas) if t.horas_consumidas is not None else None}
        for t in terapeuta.tags.all()
    ]
    # Pacientes do terapeuta (para alocar num horário pelo calendário).
    pacientes_lista = [
        {'id': p.pk_paciente, 'nome': p.nome}
        for p in terapeuta.paciente_set.filter(is_active=True).order_by('nome')
    ]
    return {
        'terapeuta_foco': terapeuta,
        'is_view_as': is_view_as,
        'can_edit': can_edit and not is_view_as,
        'titulo': titulo,
        'blocos_json': json.dumps(blocos),
        'pacientes_json': json.dumps(pacientes),
        'pacientes_lista_json': json.dumps(pacientes_lista),
        'tags_json': json.dumps(tags),
        'cap_ocupado': terapeuta.horas_ocupadas,
        'cap_total': terapeuta.horas_total,
        'cap_livres': terapeuta.horas_livres,
        'horas_recomendadas': Terapeuta.HORAS_RECOMENDADAS,
        'cap_fora': terapeuta.horas_fora_da_recomendacao,
    }


class MeusHorariosView(TerapeutaRequiredMixin, TemplateView):
    """O terapeuta logado edita o próprio calendário semanal (disponibilidade +
    blocos de atividade/tag). Em modo supervisão (D11b) fica somente-leitura."""
    template_name = 'horarios/meus_horarios.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.terapeuta, self.is_view_as = terapeuta_em_foco(request)
            if request.user.is_staff and self.terapeuta is None:
                return redirect('controle-terapeutas')
            if self.terapeuta is None:
                messages.error(request, 'Seu usuário não está vinculado a um terapeuta.')
                return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(_horarios_contexto(
            self.terapeuta, self.is_view_as, 'Meus Horários', can_edit=True))
        return ctx


def _parse_hhmm(valor):
    """'HH:MM' → time, exigindo minutos múltiplos de 30. Erro → ValueError."""
    hh, mm = valor.split(':')
    t = time(int(hh), int(mm))
    if t.minute not in (0, 30):
        raise ValueError('Horário deve ser em intervalos de 30 minutos.')
    return t


@login_required
@require_http_methods(["POST"])
def salvar_horarios_view(request, pk):
    """Substitui o calendário de um terapeuta (API do grid). Terapeuta salva o
    próprio; gestor salva o de qualquer um. Modo supervisão é só-leitura.
    Se o total de horas ≠ recomendado, avisa o terapeuta (in-system + WhatsApp
    stub), sem bloquear (decisão: 15h é recomendação)."""
    terapeuta = get_object_or_404(Terapeuta, pk=pk)
    if not request.user.is_staff:
        meu, is_view_as = terapeuta_em_foco(request)
        if is_view_as or meu is None or meu.pk_terapeuta != terapeuta.pk_terapeuta:
            return JsonResponse({'detail': 'Sem permissão.'}, status=403)

    try:
        payload = json.loads(request.body or '{}')
        itens = payload['blocos']
        assert isinstance(itens, list)
    except (json.JSONDecodeError, KeyError, AssertionError):
        return JsonResponse({'detail': 'Payload inválido.'}, status=400)

    tags_validas = set(terapeuta.tags.values_list('pk_tag', flat=True))
    novos, por_dia = [], {}
    for it in itens:
        try:
            dia = int(it['dia'])
            ini = _parse_hhmm(it['inicio'])
            fim = _parse_hhmm(it['fim'])
        except (KeyError, ValueError, TypeError):
            return JsonResponse({'detail': 'Bloco com dados inválidos.'}, status=400)
        if dia < 0 or dia > 6 or fim <= ini:
            return JsonResponse({'detail': 'Dia ou intervalo inválido.'}, status=400)
        tag_id = it.get('tag_id')
        if tag_id not in (None, '') and int(tag_id) not in tags_validas:
            return JsonResponse(
                {'detail': 'Atividade não atribuída a este terapeuta.'}, status=400)
        # Checagem de sobreposição no mesmo dia.
        for (oi, of) in por_dia.get(dia, []):
            if ini < of and oi < fim:
                return JsonResponse(
                    {'detail': 'Há blocos sobrepostos no mesmo dia.'}, status=400)
        por_dia.setdefault(dia, []).append((ini, fim))
        novos.append((dia, ini, fim, int(tag_id) if tag_id not in (None, '') else None))

    with transaction.atomic():
        terapeuta.horarios.all().delete()
        for dia, ini, fim, tag_id in novos:
            HorarioDisponivel.objects.create(
                fk_terapeuta=terapeuta, dia_semana=dia,
                hora_inicio=ini, hora_fim=fim, fk_tag_id=tag_id,
            )

    aviso = _avisar_horas_fora(terapeuta)
    return JsonResponse({
        'ok': True,
        'cap_ocupado': float(terapeuta.horas_ocupadas),
        'cap_total': float(terapeuta.horas_total),
        'cap_livres': float(terapeuta.horas_livres),
        'recomendado': Terapeuta.HORAS_RECOMENDADAS,
        'fora': terapeuta.horas_fora_da_recomendacao,
        'aviso': aviso,
    })


def _avisar_horas_fora(terapeuta):
    """Se o total ≠ recomendado, cria notificação in-system e tenta WhatsApp
    (stub). Retorna o texto do aviso ou None."""
    if not terapeuta.horas_fora_da_recomendacao:
        return None
    from principais.models import Notificacao
    from principais.whatsapp import enviar_whatsapp
    total = terapeuta.horas_total
    rec = Terapeuta.HORAS_RECOMENDADAS
    relacao = 'abaixo' if total < rec else 'acima'
    texto = (
        f"Suas horas disponíveis somam {total}h, {relacao} da recomendação de "
        f"{rec}h. Ajuste seu calendário quando puder."
    )
    assoc = terapeuta.fk_associado
    # Dedupe: remove avisos de horas anteriores ainda não lidos para não
    # acumular notificações repetidas a cada salvamento.
    Notificacao.objects.filter(
        destinatario=assoc, lida=False,
        texto__startswith='Suas horas disponíveis somam',
    ).delete()
    Notificacao.objects.create(destinatario=assoc, texto=texto)
    if assoc.telefone:
        enviar_whatsapp(assoc.telefone, texto)
    return texto


@login_required
@require_http_methods(["POST"])
def alocar_paciente_horario_view(request, pk):
    """Adiciona uma sessão semanal (dia + hora, 1h) de um paciente do terapeuta,
    a partir do calendário. Um paciente pode ter várias sessões. Terapeuta aloca
    os próprios pacientes; gestor, de qualquer um. Modo supervisão é só-leitura.
    Respeita o teto de horas (não aloca se não houver hora livre)."""
    from principais.models import SessaoSemanal
    terapeuta = get_object_or_404(Terapeuta, pk=pk)
    if not request.user.is_staff:
        meu, is_view_as = terapeuta_em_foco(request)
        if is_view_as or meu is None or meu.pk_terapeuta != terapeuta.pk_terapeuta:
            return JsonResponse({'detail': 'Sem permissão.'}, status=403)
    try:
        payload = json.loads(request.body or '{}')
        paciente_id = int(payload['paciente_id'])
        dia = int(payload['dia'])
        ini = _parse_hhmm(payload['inicio'])
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return JsonResponse({'detail': 'Dados inválidos.'}, status=400)
    if dia < 0 or dia > 6:
        return JsonResponse({'detail': 'Dia inválido.'}, status=400)
    paciente = Paciente.objects.filter(
        pk_paciente=paciente_id, fk_terapeuta=terapeuta, is_active=True).first()
    if not paciente:
        return JsonResponse({'detail': 'Paciente não é deste terapeuta.'}, status=400)
    if SessaoSemanal.objects.filter(
            fk_paciente=paciente, dia_semana=dia, hora_inicio=ini).exists():
        return JsonResponse({'detail': 'Este paciente já tem sessão nesse horário.'}, status=400)
    if terapeuta.horas_livres < Decimal('1'):
        return JsonResponse(
            {'detail': f'Sem horas livres ({terapeuta.horas_ocupadas}/{terapeuta.horas_total}h).'},
            status=400)
    sessao = SessaoSemanal.objects.create(
        fk_paciente=paciente, dia_semana=dia, hora_inicio=ini)
    fim = time((ini.hour + 1) % 24, ini.minute)
    return JsonResponse({
        'ok': True, 'sessao_id': sessao.pk, 'paciente_id': paciente.pk_paciente,
        'nome': paciente.nome, 'inicio': _hhmm(ini), 'fim': _hhmm(fim),
    })


@login_required
@require_http_methods(["POST"])
def remover_sessao_view(request, pk):
    """Remove uma sessão semanal (pelo id da sessão). Terapeuta remove as dos
    próprios pacientes; gestor, de qualquer um."""
    from principais.models import SessaoSemanal
    sessao = get_object_or_404(SessaoSemanal, pk=pk)
    terapeuta = sessao.fk_paciente.fk_terapeuta
    if not request.user.is_staff:
        meu, is_view_as = terapeuta_em_foco(request)
        if is_view_as or meu is None or terapeuta is None or \
                meu.pk_terapeuta != terapeuta.pk_terapeuta:
            return JsonResponse({'detail': 'Sem permissão.'}, status=403)
    sessao.delete()
    return JsonResponse({'ok': True})


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
    """O gestor edita o calendário de qualquer terapeuta (D11)."""
    template_name = 'horarios/meus_horarios.html'

    def dispatch(self, request, *args, **kwargs):
        self.terapeuta = get_object_or_404(Terapeuta, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        titulo = f'Horários de {self.terapeuta.fk_associado.nome}'
        ctx.update(_horarios_contexto(self.terapeuta, False, titulo, can_edit=True))
        return ctx
