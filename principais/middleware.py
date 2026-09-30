"""Middleware que bloqueia escrita no modo supervisão (D11b)."""
from django.http import HttpResponseForbidden
from django.urls import Resolver404, resolve

from principais.supervisao import is_view_as_active

# Ações de escrita permitidas mesmo em modo supervisão: só entrar/voltar e sair.
WHITELIST_VIEW_NAMES = {
    "supervisao_visualizar",
    "supervisao_voltar",
    "logout",
}


class BloqueiaEscritaEmViewAsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and is_view_as_active(request):
            try:
                view_name = resolve(request.path_info).url_name
            except Resolver404:
                view_name = None
            if view_name not in WHITELIST_VIEW_NAMES:
                return HttpResponseForbidden(
                    "Modo supervisão (somente-leitura) ativo: ações de escrita "
                    "bloqueadas. Volte à sua visualização para continuar."
                )
        return self.get_response(request)
