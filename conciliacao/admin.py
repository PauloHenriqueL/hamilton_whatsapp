from django.contrib import admin

from conciliacao.models import ExtratoOFX, TransacaoOFX


@admin.register(ExtratoOFX)
class ExtratoOFXAdmin(admin.ModelAdmin):
    list_display = ('arquivo_nome', 'conta', 'data_inicio', 'data_fim', 'created_at')
    search_fields = ('arquivo_nome', 'hash_arquivo')


@admin.register(TransacaoOFX)
class TransacaoOFXAdmin(admin.ModelAdmin):
    list_display = ('data', 'nome_pagador', 'valor', 'status_conciliacao',
                    'valor_divergente', 'fk_paciente')
    list_filter = ('status_conciliacao', 'valor_divergente')
    search_fields = ('nome_pagador', 'fitid')
    raw_id_fields = ('fk_paciente', 'fk_extrato')
