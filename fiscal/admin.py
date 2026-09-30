from django.contrib import admin

from fiscal.models import NotaFiscal


@admin.register(NotaFiscal)
class NotaFiscalAdmin(admin.ModelAdmin):
    list_display = ('fk_paciente', 'mes_competencia', 'valor', 'status_nfs', 'id_nfs')
    list_filter = ('status_nfs', 'mes_competencia')
    search_fields = ('fk_paciente__nome', 'id_nfs')
    raw_id_fields = ('fk_paciente',)
