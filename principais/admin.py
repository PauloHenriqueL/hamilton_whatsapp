from django.contrib import admin

from principais.models import (
    Abordagem, Associado, HorarioDisponivel, Paciente, Tag, Terapeuta,
)


@admin.register(Abordagem)
class AbordagemAdmin(admin.ModelAdmin):
    list_display = ('pk_abordagem', 'abordagem')
    search_fields = ('abordagem',)


@admin.register(Associado)
class AssociadoAdmin(admin.ModelAdmin):
    list_display = ('pk_associado', 'nome', 'email', 'telefone', 'is_active', 'usuario')
    list_filter = ('is_active',)
    search_fields = ('nome', 'email', 'cpf')
    raw_id_fields = ('usuario',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('pk_tag', 'nome', 'horas_consumidas', 'descricao')
    search_fields = ('nome',)


@admin.register(Terapeuta)
class TerapeutaAdmin(admin.ModelAdmin):
    list_display = ('pk_terapeuta', 'fk_associado', 'fk_abordagem', 'fk_supervisor',
                    'pacientes_max', 'is_active')
    list_filter = ('is_active', 'fk_abordagem')
    search_fields = ('fk_associado__nome',)
    raw_id_fields = ('fk_associado', 'fk_supervisor')
    filter_horizontal = ('tags', 'tags_apto')


@admin.register(HorarioDisponivel)
class HorarioDisponivelAdmin(admin.ModelAdmin):
    list_display = ('fk_terapeuta', 'dia_semana', 'hora_inicio', 'hora_fim', 'fk_tag')
    list_filter = ('dia_semana', 'fk_tag')


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('pk_paciente', 'nome', 'fk_terapeuta', 'vlr_sessao', 'is_active')
    list_filter = ('is_active', 'origem_paciente')
    search_fields = ('nome', 'cpf', 'email')
    raw_id_fields = ('fk_terapeuta',)
