"""Forms da app principais."""
from django import forms

from principais.models import Paciente


class PacienteFilterForm(forms.Form):
    """Filtros da tela Controle de Pacientes (D7). Sem o filtro de captação do
    Hamilton antigo (decisão #13)."""
    data_inicial = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Data Inicial",
    )
    data_final = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Data Final",
    )
    status_atendimento = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos')] + Paciente.STATUS_CHOICES,
        label="Status",
    )
