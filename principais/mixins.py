"""
Mixins de papel (D4).

Dois papéis no Hamilton 2.0 (decisões #1/#16):
  - Gestor  = ``User.is_staff`` → acesso total às telas de gestão.
  - Terapeuta = usuário não-staff, resolvido para um ``Terapeuta`` via
    ``request.user → Associado → Terapeuta``.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class StaffRequiredMixin(LoginRequiredMixin):
    """Exige usuário autenticado e ``is_staff`` (gestor). Portado de
    ``views_controle_terapeutas.py`` do Hamilton antigo."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if not request.user.is_staff:
            raise PermissionDenied("Acesso restrito a gestores.")
        return super().dispatch(request, *args, **kwargs)


def terapeuta_do_usuario(user):
    """Resolve o ``Terapeuta`` vinculado ao usuário logado, ou ``None``.

    Caminho do vínculo: ``User`` ─OneToOne→ ``Associado`` ─FK→ ``Terapeuta``.
    Import tardio porque os models de cadastro só nascem na D5; até lá esta
    função devolve ``None`` sem quebrar o shell.
    """
    if not getattr(user, 'is_authenticated', False):
        return None
    try:
        from principais.models import Terapeuta  # noqa: PLC0415 (import tardio proposital)
    except (ImportError, Exception):  # models ainda não existem (pré-D5)
        return None
    return (
        Terapeuta.objects
        .filter(fk_associado__usuario=user)
        .select_related('fk_associado')
        .first()
    )


def terapeuta_em_foco(request):
    """Resolve o terapeuta cuja área está sendo vista e se é modo view-as.

    Retorna ``(terapeuta, is_view_as)``. Delega à supervisão (D11b): no modo
    "ver como", devolve o supervisionado em foco com ``is_view_as=True``; fora
    dele, o próprio terapeuta do usuário.
    """
    from principais.supervisao import get_terapeuta_visualizado  # import tardio (evita ciclo)
    return get_terapeuta_visualizado(request)


class TerapeutaRequiredMixin(LoginRequiredMixin):
    """Exige um terapeuta logado (não-staff vinculado a um ``Terapeuta``).

    Deixa ``self.terapeuta`` disponível na view. O modo supervisão ("ver como")
    entra na D11b e passará a resolver o "terapeuta em foco" aqui.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        # Resolve o terapeuta EM FOCO (respeita o modo supervisão da D11b),
        # não o logado — assim view-as troca a área vista.
        self.terapeuta, self.is_view_as = terapeuta_em_foco(request)
        return super().dispatch(request, *args, **kwargs)
