"""Context processor da supervisão (D11b): alimenta o seletor no header."""
from principais.supervisao import (
    SESSION_KEY, _meu_terapeuta, eh_supervisor, supervisionados_de,
)


def supervisao(request):
    if not request.user.is_authenticated:
        return {}
    meu = _meu_terapeuta(request)
    if not eh_supervisor(meu):
        return {"is_supervisor": False}

    ctx = {
        "is_supervisor": True,
        "supervisionados": supervisionados_de(meu),
    }
    view_as_id = request.session.get(SESSION_KEY)
    if view_as_id:
        alvo = supervisionados_de(meu).filter(pk=view_as_id).first()
        if alvo:
            ctx["view_as_active"] = True
            ctx["view_as_terapeuta"] = alvo
    return ctx
