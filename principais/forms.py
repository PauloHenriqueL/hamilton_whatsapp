"""Forms da app principais."""
from django import forms

from principais.models import HorarioDisponivel, PagadorAlternativo, Paciente, Terapeuta


HorarioDisponivelFormSet = forms.inlineformset_factory(
    parent_model=Terapeuta,
    model=HorarioDisponivel,
    fields=('dia_semana', 'hora_inicio', 'hora_fim'),
    widgets={
        'dia_semana': forms.Select(attrs={'class': 'form-select'}),
        'hora_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control', 'step': 1800}),
        'hora_fim': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control', 'step': 1800}),
    },
    extra=1,
    can_delete=True,
)


PagadorAlternativoFormSet = forms.inlineformset_factory(
    parent_model=Paciente,
    model=PagadorAlternativo,
    fields=('nome',),
    widgets={
        'nome': forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex.: Maria Aparecida (mãe), Rodolpho Lima (pai)',
        }),
    },
    extra=1,
    can_delete=True,
)


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
    situacao = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Todos'),
            ('ativos', 'Ativos'),
            ('inativos', 'Inativos'),
            ('aguardando', 'Aguardando encaminhamento'),
        ],
        label="Situação",
    )


class PacienteForm(forms.ModelForm):
    """Cadastro/edição de paciente (D10), com os campos fiscais da NFS-e.
    Sem clínica/captação/modalidade (decisão #13)."""

    class Meta:
        model = Paciente
        fields = [
            'nome', 'email', 'telefone', 'contato_apoio', 'dat_nascimento',
            'fk_terapeuta', 'vlr_sessao', 'origem',
            'origem_paciente', 'is_active',
            'observacao',
            # Campos fiscais
            'cpf', 'cep', 'endereco', 'numero', 'complemento', 'bairro', 'cidade', 'uf',
        ]
        widgets = {
            'dat_nascimento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'cep': forms.TextInput(attrs={'placeholder': '00000-000'}),
            'observacao': forms.Textarea(attrs={'rows': 3}),
            'is_active': forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fk_terapeuta'].queryset = (
            Terapeuta.objects.filter(is_active=True).select_related('fk_associado')
            .order_by('fk_associado__nome')
        )
        self.fields['fk_terapeuta'].label_from_instance = lambda obj: obj.fk_associado.nome
        self.fields['fk_terapeuta'].required = False
        # Estilização Bootstrap, como no Hamilton.
        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault('class', 'form-select')
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'form-check-input')
            else:
                field.widget.attrs.setdefault('class', 'form-control')
