"""
Roteamento do Hamilton 2.0.

Rotas limpas na raiz (sem prefixo /api/v1/ do Hamilton antigo). Nesta fase as
telas de gestão e o portal do terapeuta são placeholders (D4); cada demanda da
Fase 1+ substitui a sua. O roteamento final é revisado na D21.
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from principais import views as p

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- Autenticação padrão Django (D4) ---
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # --- Home: despacha por papel (gestor → dashboard; terapeuta → horários) ---
    path('', p.HomeView.as_view(), name='dashboard'),

    # --- Telas de gestão (gate is_staff) — placeholders até suas demandas ---
    path('pacientes/', p.PacientesPlaceholderView.as_view(), name='controle-pacientes'),
    path('terapeutas/', p.TerapeutasPlaceholderView.as_view(), name='controle-terapeutas'),
    path('encaminhamento/', p.EncaminhamentoPlaceholderView.as_view(), name='encaminhamento'),
    path('conciliacao/', p.ConciliacaoPlaceholderView.as_view(), name='conciliacao'),
    path('notas/', p.NotasPlaceholderView.as_view(), name='notas'),

    # --- Portal do terapeuta (não-staff) — placeholders até D11 ---
    path('meus-horarios/', p.MeusHorariosPlaceholderView.as_view(), name='meus-horarios'),
    path('meus-pacientes/', p.MeusPacientesPlaceholderView.as_view(), name='meus-pacientes'),
]
