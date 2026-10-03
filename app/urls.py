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
from principais import views_controle_terapeutas as ct
from conciliacao import views as conc
from dashboard.views import DashboardView
from fiscal import views as fiscal

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- Autenticação padrão Django (D4) ---
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # --- Home: dashboard do gestor; terapeuta é redirecionado para horários ---
    path('', DashboardView.as_view(), name='dashboard'),

    # --- Controle de Pacientes (D7) ---
    path('pacientes/', p.ControlePacientesView.as_view(), name='controle-pacientes'),
    # CRUD de paciente (D10).
    path('pacientes/novo/', p.PacienteCreateView.as_view(), name='paciente-create'),
    path('pacientes/<int:pk>/', p.PacienteDetailView.as_view(), name='paciente-detail'),
    path('pacientes/<int:pk>/editar/', p.PacienteUpdateView.as_view(), name='paciente-update'),
    path('pacientes/<int:pk>/duplicar/', p.PacienteDuplicarView.as_view(), name='paciente-duplicar'),
    path('pacientes/<int:pk>/inativar/', p.PacienteDeleteView.as_view(), name='paciente-delete'),

    # --- Encaminhamento (D8) ---
    path('encaminhamento/', p.EncaminhamentoView.as_view(), name='encaminhamento'),
    path('encaminhamento/alocar/', p.alocar_terapeuta_view, name='alocar_terapeuta'),

    # --- Controle de Terapeutas (D9) ---
    path('terapeutas/', ct.ControleTerapeutasView.as_view(), name='controle-terapeutas'),
    path('terapeutas/tags/', ct.TagCreateAPI.as_view(), name='controle-terapeutas-tag-create'),
    path('terapeutas/tags/<int:pk>/', ct.TagDetailAPI.as_view(), name='controle-terapeutas-tag-detail'),
    path('terapeutas/<int:pk>/tags-atuais/', ct.TerapeutaTagsAtuaisAPI.as_view(), name='controle-terapeutas-tags-atuais'),
    path('terapeutas/<int:pk>/tags-apto/', ct.TerapeutaTagsAptoAPI.as_view(), name='controle-terapeutas-tags-apto'),
    path('terapeutas/<int:pk>/max/', ct.TerapeutaMaxAPI.as_view(), name='controle-terapeutas-max'),

    # --- Conciliação / OFX (D13–D15) ---
    path('conciliacao/', conc.PainelConciliacaoView.as_view(), name='conciliacao-painel'),
    path('conciliacao/importar/', conc.ImportarOFXView.as_view(), name='conciliacao-importar'),
    path('conciliacao/<int:pk>/associar/', conc.associar_paciente_view, name='conciliacao-associar'),

    # --- Notas Fiscais (D17–D19) ---
    path('notas/', fiscal.painel_notas_fiscais, name='painel_notas_fiscais'),
    path('notas/fechar-mes/', fiscal.fechar_mes, name='fechar_mes'),
    path('notas/<int:pk>/emitir/', fiscal.emitir_nota, name='emitir_nota'),
    path('notas/emitir-lote/', fiscal.emitir_notas_lote, name='emitir_notas_lote'),
    path('notas/<int:pk>/consultar/', fiscal.consultar_nota, name='consultar_nota'),
    path('notas/<int:pk>/cancelar/', fiscal.cancelar_nota, name='cancelar_nota'),
    path('notas/<int:pk>/pdf/', fiscal.download_pdf_nfs, name='download_pdf_nfs'),
    path('notas/<int:pk>/xml/', fiscal.download_xml_nfs, name='download_xml_nfs'),
    path('notas/exportar-lote/', fiscal.exportar_notas_lote, name='exportar_notas_lote'),

    # --- Portal do terapeuta (não-staff) — D11 ---
    path('meus-horarios/', p.MeusHorariosView.as_view(), name='meus-horarios'),
    path('meus-pacientes/', p.MeusPacientesView.as_view(), name='meus-pacientes'),
    # Gestor edita horários de um terapeuta específico.
    path('terapeutas/<int:pk>/horarios/', p.GerenciarHorariosView.as_view(), name='gerenciar-horarios'),
    # Salvar calendário (API JSON do grid) — terapeuta (próprio) ou gestor.
    path('terapeutas/<int:pk>/horarios/salvar/', p.salvar_horarios_view, name='salvar-horarios'),

    # --- Notificações in-system (D14b) ---
    path('notificacoes/<int:pk>/lida/', p.notificacao_marcar_lida, name='notificacao-marcar-lida'),

    # --- Modo supervisão (D11b) ---
    path('supervisao/ver/<int:pk>/', p.supervisao_visualizar, name='supervisao_visualizar'),
    path('supervisao/voltar/', p.supervisao_voltar, name='supervisao_voltar'),
]
