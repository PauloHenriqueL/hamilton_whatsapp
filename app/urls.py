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

    # --- Controle de Pacientes (D7) ---
    path('pacientes/', p.ControlePacientesView.as_view(), name='controle-pacientes'),
    # CRUD de paciente — placeholders até a D10.
    path('pacientes/novo/', p.paciente_placeholder, name='paciente-create'),
    path('pacientes/<int:pk>/', p.paciente_placeholder, name='paciente-detail'),
    path('pacientes/<int:pk>/editar/', p.paciente_placeholder, name='paciente-update'),
    path('pacientes/<int:pk>/duplicar/', p.paciente_placeholder, name='paciente-duplicar'),
    path('pacientes/<int:pk>/inativar/', p.paciente_placeholder, name='paciente-delete'),

    # --- Encaminhamento (D8) ---
    path('encaminhamento/', p.EncaminhamentoView.as_view(), name='encaminhamento'),
    path('encaminhamento/alocar/', p.alocar_terapeuta_view, name='alocar_terapeuta'),

    # --- Telas de gestão — placeholders até suas demandas ---
    path('terapeutas/', p.TerapeutasPlaceholderView.as_view(), name='controle-terapeutas'),
    path('conciliacao/', p.ConciliacaoPlaceholderView.as_view(), name='conciliacao'),
    path('notas/', p.NotasPlaceholderView.as_view(), name='notas'),

    # --- Portal do terapeuta (não-staff) — placeholders até D11 ---
    path('meus-horarios/', p.MeusHorariosPlaceholderView.as_view(), name='meus-horarios'),
    path('meus-pacientes/', p.MeusPacientesPlaceholderView.as_view(), name='meus-pacientes'),
]
