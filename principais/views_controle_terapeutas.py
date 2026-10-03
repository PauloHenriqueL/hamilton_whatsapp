import json

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import IntegrityError
from django.db.models import Count, Prefetch, Q
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

from .models import HorarioDisponivel, Paciente, Tag, Terapeuta


DIAS_SEMANA_CHOICES = HorarioDisponivel.DIAS_SEMANA
DIAS_ABREV = {0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sáb", 6: "Dom"}


def _staff_only(user):
    return user.is_authenticated and user.is_staff


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return _staff_only(self.request.user)


class ControleTerapeutasView(StaffRequiredMixin, TemplateView):
    template_name = "controle_terapeutas/lista.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        req = self.request

        nome = req.GET.get("nome", "").strip()
        pacientes_min = _parse_int(req.GET.get("pacientes_min"))
        pacientes_max = _parse_int(req.GET.get("pacientes_max"))
        dias = [int(d) for d in req.GET.getlist("dia") if d.isdigit()]
        tag_atual_ids = [int(t) for t in req.GET.getlist("tag_atual") if t.isdigit()]
        tag_apto_ids = [int(t) for t in req.GET.getlist("tag_apto") if t.isdigit()]
        ativo = req.GET.get("ativo", "todos")
        order_by = req.GET.get("order_by", "")
        direction = req.GET.get("dir", "asc")

        qs = (
            Terapeuta.objects
            .select_related("fk_associado")
            .prefetch_related(
                "tags",
                "tags_apto",
                Prefetch(
                    "horarios",
                    queryset=HorarioDisponivel.objects.select_related("fk_tag")
                    .order_by("dia_semana", "hora_inicio"),
                ),
            )
            .annotate(
                pacientes_ativos=Count(
                    "paciente",
                    filter=Q(paciente__is_active=True),
                    distinct=True,
                ),
            )
        )

        if nome:
            qs = qs.filter(fk_associado__nome__icontains=nome)
        if pacientes_min is not None:
            qs = qs.filter(pacientes_ativos__gte=pacientes_min)
        if pacientes_max is not None:
            qs = qs.filter(pacientes_ativos__lte=pacientes_max)
        if dias:
            qs = qs.filter(horarios__dia_semana__in=dias).distinct()
        if tag_atual_ids:
            qs = qs.filter(tags__pk_tag__in=tag_atual_ids).distinct()
        if tag_apto_ids:
            qs = qs.filter(tags_apto__pk_tag__in=tag_apto_ids).distinct()
        if ativo == "ativos":
            qs = qs.filter(is_active=True)
        elif ativo == "inativos":
            qs = qs.filter(is_active=False)

        order_field_map = {
            "nome": "fk_associado__nome",
            "pacientes": "pacientes_ativos",
            "is_active": "is_active",
        }
        if order_by in order_field_map:
            field = order_field_map[order_by]
            if direction == "desc":
                field = "-" + field
            qs = qs.order_by(field)
        else:
            qs = qs.order_by("-is_active", "fk_associado__nome")

        terapeutas = list(qs)
        from decimal import Decimal
        for t in terapeutas:
            horarios = list(t.horarios.all())
            t.horarios_por_dia = _horarios_agrupados(horarios)
            # Capacidade por horas (ver memória hamilton2-horarios-capacidade).
            total = sum((h.duracao_horas for h in horarios), Decimal("0"))
            tags_h = sum((h.duracao_horas for h in horarios if h.fk_tag_id), Decimal("0"))
            ocupado = tags_h + Decimal(t.pacientes_ativos)
            t.cap_total = total
            t.cap_ocupado = ocupado
            t.cap_livres = total - ocupado
            t.cap_fora_recomendacao = total != Decimal(Terapeuta.HORAS_RECOMENDADAS)

        ctx.update({
            "terapeutas": terapeutas,
            "tags": list(Tag.objects.all()),
            "horas_recomendadas": Terapeuta.HORAS_RECOMENDADAS,
            "dias_semana": DIAS_SEMANA_CHOICES,
            "filtros": {
                "nome": nome,
                "pacientes_min": req.GET.get("pacientes_min", ""),
                "pacientes_max": req.GET.get("pacientes_max", ""),
                "dias": dias,
                "tag_atual": tag_atual_ids,
                "tag_apto": tag_apto_ids,
                "ativo": ativo,
                "order_by": order_by,
                "dir": direction,
            },
        })
        return ctx


def _parse_int(raw):
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _painel_substitutos():
    """Para cada tag-atividade: quem dá hoje (tem bloco no calendário, com
    dia/hora) e quem está apto a dar (tag em ``tags_apto``, sem bloco ainda).
    É o insumo do gestor para achar substituto (a entrega-chave)."""
    # Quem dá: blocos de calendário com fk_tag.
    blocos = (
        HorarioDisponivel.objects.filter(fk_tag__isnull=False)
        .select_related("fk_tag", "fk_terapeuta__fk_associado")
        .order_by("fk_tag__nome", "dia_semana", "hora_inicio")
    )
    da_por_tag = {}
    terapeutas_que_dao = {}
    for b in blocos:
        tid = b.fk_tag_id
        da_por_tag.setdefault(tid, []).append({
            "terapeuta": b.fk_terapeuta.fk_associado.nome,
            "pk_terapeuta": b.fk_terapeuta_id,
            "dia": DIAS_ABREV.get(b.dia_semana, "?"),
            "inicio": b.hora_inicio.strftime("%H:%M"),
            "fim": b.hora_fim.strftime("%H:%M"),
        })
        terapeutas_que_dao.setdefault(tid, set()).add(b.fk_terapeuta_id)

    # Quem é apto: tags_apto, menos quem já dá.
    aptos_por_tag = {}
    for tag in Tag.objects.prefetch_related("terapeutas_aptos__fk_associado"):
        ja_dao = terapeutas_que_dao.get(tag.pk_tag, set())
        aptos = [
            {"terapeuta": t.fk_associado.nome, "pk_terapeuta": t.pk_terapeuta}
            for t in tag.terapeutas_aptos.all()
            if t.is_active and t.pk_terapeuta not in ja_dao
        ]
        aptos_por_tag[tag.pk_tag] = aptos

    atividades = []
    for tag in Tag.objects.order_by("nome"):
        da = da_por_tag.get(tag.pk_tag, [])
        aptos = aptos_por_tag.get(tag.pk_tag, [])
        # Só mostra tags que são de fato atividades (alguém dá ou está apto, ou
        # tem tempo padrão definido). Evita poluir com rótulos como 'supervisor'.
        if not da and not aptos and not tag.horas_consumidas:
            continue
        atividades.append({
            "pk_tag": tag.pk_tag,
            "nome": tag.nome,
            "descricao": tag.descricao,
            "horas_consumidas": tag.horas_consumidas,
            "quem_da": da,
            "quem_apto": aptos,
        })
    return atividades


def _horarios_agrupados(horarios):
    por_dia = {}
    for h in horarios:
        por_dia.setdefault(h.dia_semana, []).append(
            f"{h.hora_inicio.strftime('%H:%M')}–{h.hora_fim.strftime('%H:%M')}"
        )
    return [
        {"abrev": DIAS_ABREV[d], "faixas": faixas}
        for d, faixas in sorted(por_dia.items())
    ]


class _StaffJsonMixin:
    def dispatch(self, request, *args, **kwargs):
        if not _staff_only(request.user):
            return JsonResponse({"detail": "Acesso restrito a staff."}, status=403)
        return super().dispatch(request, *args, **kwargs)


def _parse_horas(raw):
    """Valida o tempo padrão da tag: None/'' = sem horas; senão Decimal >= 0.
    Retorna (valor, erro)."""
    from decimal import Decimal, InvalidOperation
    if raw in (None, ""):
        return None, None
    try:
        valor = Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return None, "Tempo padrão inválido (use um número, ex.: 2 ou 1.5)."
    if valor < 0:
        return None, "Tempo padrão não pode ser negativo."
    return valor, None


def _tag_payload(tag):
    return {
        "pk_tag": tag.pk_tag,
        "nome": tag.nome,
        "horas_consumidas": str(tag.horas_consumidas) if tag.horas_consumidas is not None else None,
        "descricao": tag.descricao or "",
    }


@method_decorator(require_http_methods(["POST"]), name="dispatch")
class TagCreateAPI(_StaffJsonMixin, View):
    def post(self, request):
        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"detail": "JSON inválido."}, status=400)
        nome = (body.get("nome") or "").strip()
        if not nome:
            return JsonResponse({"detail": "Informe o nome da tag."}, status=400)
        if len(nome) > 80:
            return JsonResponse({"detail": "Nome muito longo (máx. 80)."}, status=400)
        horas, erro = _parse_horas(body.get("horas_consumidas"))
        if erro:
            return JsonResponse({"detail": erro}, status=400)
        descricao = (body.get("descricao") or "").strip() or None
        try:
            tag = Tag.objects.create(nome=nome, horas_consumidas=horas, descricao=descricao)
        except IntegrityError:
            return JsonResponse({"detail": "Já existe uma tag com esse nome."}, status=400)
        return JsonResponse(_tag_payload(tag), status=201)


@method_decorator(require_http_methods(["PATCH", "DELETE"]), name="dispatch")
class TagDetailAPI(_StaffJsonMixin, View):
    def patch(self, request, pk):
        tag = get_object_or_404(Tag, pk=pk)
        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"detail": "JSON inválido."}, status=400)
        nome = (body.get("nome") or "").strip()
        if not nome:
            return JsonResponse({"detail": "Informe o nome da tag."}, status=400)
        if len(nome) > 80:
            return JsonResponse({"detail": "Nome muito longo (máx. 80)."}, status=400)
        horas, erro = _parse_horas(body.get("horas_consumidas"))
        if erro:
            return JsonResponse({"detail": erro}, status=400)
        tag.nome = nome
        tag.horas_consumidas = horas
        tag.descricao = (body.get("descricao") or "").strip() or None
        try:
            tag.save()
        except IntegrityError:
            return JsonResponse({"detail": "Já existe uma tag com esse nome."}, status=400)
        return JsonResponse(_tag_payload(tag))

    def delete(self, request, pk):
        tag = get_object_or_404(Tag, pk=pk)
        tag.delete()
        return JsonResponse({"detail": "Tag removida."})


@method_decorator(require_http_methods(["PATCH"]), name="dispatch")
class TerapeutaTagsAPI(_StaffJsonMixin, View):
    field = "tags"

    def patch(self, request, pk):
        terapeuta = get_object_or_404(Terapeuta, pk=pk)
        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"detail": "JSON inválido."}, status=400)
        ids = body.get("tags")
        if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
            return JsonResponse({"detail": "Campo 'tags' deve ser lista de ids inteiros."}, status=400)
        tags = list(Tag.objects.filter(pk_tag__in=ids))
        if len(tags) != len(set(ids)):
            return JsonResponse({"detail": "Alguma tag informada não existe."}, status=400)
        getattr(terapeuta, self.field).set(tags)
        return JsonResponse({
            "pk_terapeuta": terapeuta.pk,
            self.field: [{"pk_tag": t.pk_tag, "nome": t.nome} for t in tags],
        })


class TerapeutaTagsAtuaisAPI(TerapeutaTagsAPI):
    field = "tags"


class TerapeutaTagsAptoAPI(TerapeutaTagsAPI):
    field = "tags_apto"


@method_decorator(require_http_methods(["PATCH"]), name="dispatch")
class TerapeutaMaxAPI(_StaffJsonMixin, View):
    """Edição inline do máximo de pacientes do terapeuta (decisão #19)."""

    def patch(self, request, pk):
        terapeuta = get_object_or_404(Terapeuta, pk=pk)
        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"detail": "JSON inválido."}, status=400)
        raw = body.get("pacientes_max", None)
        # Permite limpar o máximo (null/vazio) ou definir um inteiro >= 0.
        if raw in (None, ""):
            valor = None
        else:
            valor = _parse_int(raw)
            if valor is None or valor < 0:
                return JsonResponse(
                    {"detail": "Informe um número inteiro não-negativo (ou vazio)."},
                    status=400,
                )
        terapeuta.pacientes_max = valor
        terapeuta.save(update_fields=["pacientes_max", "updated_at"])
        return JsonResponse({
            "pk_terapeuta": terapeuta.pk_terapeuta,
            "pacientes_max": terapeuta.pacientes_max,
        })
