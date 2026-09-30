"""
Modo supervisão ("ver como" supervisionado) — D11b.

Portado do Hamilton, adaptando ``fk_decano``/``is_decano`` para o modelo 2.0
(decisão #7): o supervisor é um ``Terapeuta`` que carrega a tag ``supervisor``
ou tem supervisionados, e o vínculo é ``Terapeuta.fk_supervisor → Terapeuta``.
"""
from principais.models import Terapeuta

SESSION_KEY = "view_as_terapeuta_id"


def _meu_terapeuta(request):
    """Terapeuta do usuário logado (via Associado.usuario). ``None`` se não há."""
    return (
        Terapeuta.objects
        .select_related('fk_associado')
        .filter(fk_associado__usuario=request.user)
        .first()
    )


def eh_supervisor(terapeuta):
    if terapeuta is None:
        return False
    return (
        terapeuta.tags.filter(nome__iexact='supervisor').exists()
        or terapeuta.supervisionados.filter(is_active=True).exists()
    )


def supervisionados_de(terapeuta):
    if terapeuta is None:
        return Terapeuta.objects.none()
    return (
        Terapeuta.objects
        .select_related('fk_associado')
        .filter(fk_supervisor=terapeuta, is_active=True)
        .order_by('fk_associado__nome')
    )


def get_terapeuta_visualizado(request):
    """Retorna ``(terapeuta_em_foco, is_view_as)``.

    Se há um supervisionado selecionado na sessão e o usuário é de fato o
    supervisor dele, devolve o supervisionado com ``is_view_as=True``. Caso
    contrário, devolve o próprio terapeuta do usuário.
    """
    if not request.user.is_authenticated:
        return None, False

    meu = _meu_terapeuta(request)
    view_as_id = request.session.get(SESSION_KEY)
    if view_as_id and meu is not None:
        alvo = supervisionados_de(meu).filter(pk=view_as_id).first()
        if alvo:
            return alvo, True
        request.session.pop(SESSION_KEY, None)
    return meu, False


def is_view_as_active(request):
    return bool(request.user.is_authenticated and request.session.get(SESSION_KEY))
