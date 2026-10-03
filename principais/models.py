"""
Models de cadastro do Hamilton 2.0 (D5).

Portados do Hamilton antigo (``principais/models.py`` + ``acessorios`` Abordagem)
no modelo ENXUTO do 2.0:

  - somem núcleo, clínica, modalidade, captação, setores, stripe, tipo_pagamento
    (decisão #13);
  - ``Terapeuta.fk_decano`` vira auto-relação ``fk_supervisor`` (decisão #7);
  - ``Tag`` ganha ``horas_consumidas`` opcional (decisão #8);
  - ``Paciente.fk_captacao`` vira o campo simples ``origem`` (decisão #13) e
    ganha os campos fiscais da NFS-e.

Os PKs ``pk_*`` e os ``db_table`` originais são preservados de propósito: a
migração de corte único (D6) copia registros do banco antigo mantendo os IDs,
o que conserva os vínculos User↔Associado↔Terapeuta e as FKs.
"""
from datetime import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator, RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# --- Validadores (portados) -------------------------------------------------
def validate_minutes(value):
    """Horário em intervalos de 30 minutos (ex.: 09:00 ou 09:30)."""
    if value.minute not in (0, 30):
        raise ValidationError(
            _('O horário deve ser em intervalos de 30 minutos (ex: 09:00 ou 09:30).'),
            code='invalid_minutes',
        )


def validar_cpf(cpf):
    if len(cpf) != 11 or not cpf.isdigit():
        raise ValidationError('CPF deve ter exatamente 11 dígitos numéricos.')
    if cpf == cpf[0] * 11:
        raise ValidationError('CPF inválido.')
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = (soma * 10) % 11
    if digito1 == 10:
        digito1 = 0
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = (soma * 10) % 11
    if digito2 == 10:
        digito2 = 0
    if cpf[-2:] != f"{digito1}{digito2}":
        raise ValidationError('CPF inválido.')


telefone_validator = RegexValidator(
    regex=r'^\d{10,11}$',
    message="O telefone deve conter 10 ou 11 dígitos numéricos. Exemplo: 31988553344",
)


class Abordagem(models.Model):
    """Abordagem terapêutica. Única tabela de apoio mantida (decisão #13)."""
    pk_abordagem = models.AutoField(primary_key=True, verbose_name="ID")
    abordagem = models.CharField(max_length=255, verbose_name="Abordagem")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")

    class Meta:
        db_table = "abordagens"
        ordering = ["abordagem"]
        verbose_name = "Abordagem"
        verbose_name_plural = "Abordagens"

    def __str__(self):
        return self.abordagem


class Associado(models.Model):
    """Dados da pessoa (terapeuta, supervisor ou gestor) + vínculo 1-1 com User
    (decisão #6). Sem setores/faculdade/decano do Hamilton antigo."""
    pk_associado = models.AutoField(primary_key=True, verbose_name="ID")
    nome = models.CharField(max_length=255, verbose_name="Nome")
    email = models.EmailField(
        null=True, blank=True, unique=True, verbose_name="E-mail",
        validators=[EmailValidator(message="Informe um endereço de e-mail válido.")],
    )
    telefone = models.CharField(
        max_length=20, verbose_name="Telefone",
        help_text="Exemplo: 31988553344 (sem +55/espaços/parênteses)",
        validators=[telefone_validator],
    )
    contato_apoio = models.CharField(
        null=True, blank=True, max_length=20,
        verbose_name="Telefone do Contato de Apoio", validators=[telefone_validator],
    )
    dat_nascimento = models.DateField(null=True, blank=True, verbose_name="Data de Nascimento")
    sexo = models.CharField(
        max_length=1, choices=[('M', 'Masculino'), ('F', 'Feminino'), ('O', 'Outro')],
        verbose_name="Sexo", null=True, blank=True,
    )
    cpf = models.CharField(
        null=True, blank=True, max_length=14, unique=True, verbose_name='CPF',
        validators=[validar_cpf], help_text='Só números. Exemplo: 12345678901',
    )
    endereco = models.CharField(
        max_length=100, blank=True, null=True, verbose_name='Endereço',
        help_text='Exemplo: MG, Belo Horizonte',
    )
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    observacao = models.TextField(null=True, blank=True, verbose_name="Observações")
    usuario = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuário",
        help_text="Usuário de login vinculado ao associado (opcional).",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")

    class Meta:
        db_table = "associados"
        ordering = ['nome']
        verbose_name = "Associado"
        verbose_name_plural = "Associados"

    def __str__(self):
        return self.nome


class Tag(models.Model):
    """Rótulo/atividade de terapeuta (atuais / apto a). ``horas_consumidas`` é o
    *tempo padrão* da atividade (duração sugerida ao alocar o bloco no
    calendário; o terapeuta pode alocar mais). ``descricao`` explica a atividade
    (ex.: "grupo de estudo toda terça")."""
    pk_tag = models.AutoField(primary_key=True, verbose_name="ID")
    nome = models.CharField(max_length=80, unique=True, verbose_name="Nome")
    horas_consumidas = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name="Tempo padrão (h)",
        help_text="Duração sugerida da atividade ao alocá-la no calendário do terapeuta.",
    )
    descricao = models.TextField(
        null=True, blank=True, verbose_name="Descrição",
        help_text="O que é a atividade (ex.: 'grupo de estudo toda terça').",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")

    class Meta:
        db_table = "tags"
        ordering = ["nome"]
        verbose_name = "Tag"
        verbose_name_plural = "Tags"

    def __str__(self):
        return self.nome


class Terapeuta(models.Model):
    """Terapeuta. Supervisor = auto-relação ``fk_supervisor`` + tag ``supervisor``
    (decisão #7). Sem núcleo/clínica/modalidade (decisão #13)."""
    pk_terapeuta = models.AutoField(primary_key=True, verbose_name="ID")
    fk_associado = models.ForeignKey(
        Associado, on_delete=models.CASCADE, db_column='fk_associado',
        verbose_name="Associado",
    )
    fk_supervisor = models.ForeignKey(
        'self', on_delete=models.SET_NULL, db_column='fk_supervisor',
        null=True, blank=True, related_name="supervisionados", verbose_name="Supervisor",
    )
    fk_abordagem = models.ForeignKey(
        Abordagem, on_delete=models.PROTECT, db_column='fk_abordagem',
        verbose_name="Abordagem", null=True, blank=True,
    )
    pacientes_max = models.IntegerField(verbose_name="Máximo de pacientes", blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    observacao = models.TextField(null=True, blank=True, verbose_name="Observações")
    link_agenda = models.CharField(max_length=255, blank=True, null=True, verbose_name="Google Agenda")
    tags = models.ManyToManyField(
        Tag, related_name="terapeutas_atuais", db_table="terapeutas_tags",
        blank=True, verbose_name="Tags atuais",
    )
    tags_apto = models.ManyToManyField(
        Tag, related_name="terapeutas_aptos", db_table="terapeutas_tags_apto",
        blank=True, verbose_name="Apto a",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")

    # Capacidade semanal recomendada (horas). É só referência: o terapeuta pode
    # cadastrar menos ou mais; o desvio dispara uma notificação (não bloqueia).
    HORAS_RECOMENDADAS = 15

    class Meta:
        db_table = "terapeutas"
        ordering = ['fk_associado__nome']
        verbose_name = "Terapeuta"
        verbose_name_plural = "Terapeutas"

    def __str__(self):
        return self.fk_associado.nome

    @property
    def is_supervisor(self):
        """É supervisor se carrega a tag ``supervisor`` ou tem supervisionados."""
        return self.tags.filter(nome__iexact='supervisor').exists() or \
            self.supervisionados.filter(is_active=True).exists()

    # --- Capacidade por horas (ver memória hamilton2-horarios-capacidade) ------
    @property
    def horas_total(self):
        """Soma (em horas) de todos os blocos cadastrados no calendário.
        É o denominador real de capacidade (o terapeuta distribui ~15h)."""
        return sum((h.duracao_horas for h in self.horarios.all()), Decimal('0'))

    @property
    def horas_tags(self):
        """Horas ocupadas por blocos de atividade/tag (fk_tag preenchido)."""
        return sum(
            (h.duracao_horas for h in self.horarios.all() if h.fk_tag_id),
            Decimal('0'),
        )

    @property
    def pacientes_ativos_count(self):
        """Pacientes ativos atendidos por este terapeuta (para o pacientes_max)."""
        return self.paciente_set.filter(is_active=True).count()

    @property
    def sessoes_count(self):
        """Sessões semanais dos pacientes ativos (cada sessão = 1h)."""
        return SessaoSemanal.objects.filter(
            fk_paciente__fk_terapeuta=self, fk_paciente__is_active=True
        ).count()

    @property
    def horas_ocupadas(self):
        """Ocupado = sessões semanais (1h cada) + blocos de atividade/tag."""
        return self.horas_tags + Decimal(self.sessoes_count)

    @property
    def horas_livres(self):
        """Horas livres para novos pacientes = total cadastrado − ocupado."""
        return self.horas_total - self.horas_ocupadas

    @property
    def horas_fora_da_recomendacao(self):
        """True se o total cadastrado difere das horas recomendadas (dispara
        aviso ao terapeuta; não bloqueia)."""
        return self.horas_total != Decimal(self.HORAS_RECOMENDADAS)


class HorarioDisponivel(models.Model):
    """Janela de disponibilidade do terapeuta — insumo do Encaminhamento (D8)."""
    DIAS_SEMANA = (
        (0, 'Segunda-feira'), (1, 'Terça-feira'), (2, 'Quarta-feira'),
        (3, 'Quinta-feira'), (4, 'Sexta-feira'), (5, 'Sábado'), (6, 'Domingo'),
    )
    fk_terapeuta = models.ForeignKey(
        Terapeuta, on_delete=models.CASCADE, related_name='horarios',
    )
    fk_tag = models.ForeignKey(
        Tag, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='blocos', verbose_name="Atividade",
        help_text="Vazio = disponível para pacientes. Preenchido = bloco desta atividade.",
    )
    dia_semana = models.IntegerField(choices=DIAS_SEMANA, verbose_name="Dia da semana")
    hora_inicio = models.TimeField(verbose_name="Horário de início", validators=[validate_minutes])
    hora_fim = models.TimeField(verbose_name="Horário de fim", validators=[validate_minutes])

    class Meta:
        verbose_name = "Horário Disponível"
        verbose_name_plural = "Horários Disponíveis"
        unique_together = ('fk_terapeuta', 'dia_semana', 'hora_inicio')
        ordering = ['fk_terapeuta', 'dia_semana', 'hora_inicio']

    def __str__(self):
        rotulo = f" [{self.fk_tag.nome}]" if self.fk_tag_id else ""
        return (f"{self.fk_terapeuta.fk_associado.nome} - {self.get_dia_semana_display()}: "
                f"{self.hora_inicio.strftime('%H:%M')} às {self.hora_fim.strftime('%H:%M')}{rotulo}")

    @property
    def duracao_horas(self):
        """Duração do bloco em horas (Decimal). Ex.: 10:00–12:00 → 2.00."""
        base = datetime(2000, 1, 1)
        delta = datetime.combine(base, self.hora_fim) - datetime.combine(base, self.hora_inicio)
        return Decimal(delta.total_seconds()) / Decimal(3600)

    @property
    def is_atividade(self):
        return self.fk_tag_id is not None


class Paciente(models.Model):
    """Paciente. ``fk_terapeuta`` nulo = aguardando encaminhamento. Sem
    clínica/captação/modalidade/stripe (decisão #13); ``origem`` substitui a
    captação. Campos fiscais exigidos pela NFS-e (decisão #4).

    Situação do paciente é só ``is_active`` (ativo/inativo). O antigo
    ``status_atendimento`` (4 estados) foi removido por ser redundante;
    "aguardando encaminhamento" passa a ser ``ativo sem fk_terapeuta``."""
    ORIGEM_CHOICES = [
        ('NOVO', 'Novo Paciente'),
        ('REENCAMINHADO', 'Reencaminhado'),
    ]

    pk_paciente = models.AutoField(primary_key=True, verbose_name="ID")
    fk_terapeuta = models.ForeignKey(
        Terapeuta, on_delete=models.SET_NULL, db_column='fk_terapeuta',
        verbose_name="Terapeuta", null=True, blank=True,
        help_text="Vazio = paciente aguardando encaminhamento.",
    )
    nome = models.CharField(max_length=255, verbose_name="Nome")
    email = models.EmailField(
        blank=True, null=True, verbose_name="E-mail",
        validators=[EmailValidator(message="Informe um endereço de e-mail válido.")],
    )
    telefone = models.CharField(
        max_length=20, verbose_name="Telefone do Paciente",
        help_text="Exemplo: 31988553344 (sem +55/espaços/parênteses)",
        validators=[telefone_validator],
    )
    contato_apoio = models.CharField(
        null=True, blank=True, max_length=20,
        verbose_name="Telefone do Contato de Apoio", validators=[telefone_validator],
    )
    dat_nascimento = models.DateField(null=True, blank=True, verbose_name="Data de Nascimento")
    vlr_sessao = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Acordado")
    origem = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Origem",
        help_text="De onde veio o paciente (substitui a antiga captação).",
    )
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    observacao = models.TextField(null=True, blank=True, verbose_name="Observações")
    origem_paciente = models.CharField(
        max_length=20, choices=ORIGEM_CHOICES, default='NOVO',
        verbose_name="Origem do Paciente",
    )
    # Os horários das sessões ficam em SessaoSemanal (um paciente pode ter mais
    # de uma sessão por semana). O antigo par dia_semana_padrao/hora_padrao foi
    # substituído por essa tabela.

    # --- Campos fiscais (NFS-e) ---
    cpf = models.CharField(
        null=True, blank=True, max_length=14, unique=True, verbose_name='CPF',
        validators=[validar_cpf], help_text='Só números. Exemplo: 12345678901',
    )
    cep = models.CharField(blank=True, null=True, max_length=9, verbose_name="CEP", help_text='Apenas números')
    endereco = models.CharField(blank=True, null=True, max_length=255, verbose_name="Endereço")
    numero = models.CharField(blank=True, null=True, max_length=20, verbose_name="Número")
    complemento = models.CharField(blank=True, null=True, max_length=100, verbose_name="Complemento")
    bairro = models.CharField(blank=True, null=True, max_length=100, verbose_name="Bairro")
    cidade = models.CharField(blank=True, null=True, max_length=100, verbose_name="Cidade", default='Belo Horizonte')
    uf = models.CharField(blank=True, null=True, max_length=2, verbose_name="UF", default='MG')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")

    class Meta:
        db_table = "pacientes"
        ordering = ['nome']
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"

    def __str__(self):
        return self.nome

    @property
    def tem_cpf(self):
        """CPF preenchido? Usado pela regra de nota (decisão #4) e pela tela."""
        return bool(self.cpf and self.cpf.strip())

    @property
    def dias_desde_criacao(self):
        """Dias desde o cadastro. Substitui 'dias sem atividade' do Hamilton
        (não há mais Consulta no 2.0) — ver D7."""
        if not self.created_at:
            return None
        return (timezone.now() - self.created_at).days


class SessaoSemanal(models.Model):
    """Sessão semanal recorrente de um paciente (1h). Um paciente pode ter mais
    de uma por semana (ex.: 2x). Substitui o par dia_semana_padrao/hora_padrao."""
    fk_paciente = models.ForeignKey(
        Paciente, on_delete=models.CASCADE, related_name='sessoes',
        verbose_name="Paciente",
    )
    dia_semana = models.IntegerField(
        choices=HorarioDisponivel.DIAS_SEMANA, verbose_name="Dia da semana")
    hora_inicio = models.TimeField(verbose_name="Horário", validators=[validate_minutes])

    class Meta:
        db_table = "sessoes_semanais"
        unique_together = ('fk_paciente', 'dia_semana', 'hora_inicio')
        ordering = ['dia_semana', 'hora_inicio']
        verbose_name = "Sessão Semanal"
        verbose_name_plural = "Sessões Semanais"

    def __str__(self):
        return (f"{self.fk_paciente.nome} - {self.get_dia_semana_display()} "
                f"{self.hora_inicio.strftime('%H:%M')}")


class Notificacao(models.Model):
    """Notificação in-system (D14b). Começa com a divergência de valor do OFX
    (decisão #15/#21): avisa o terapeuta e o supervisor quando um pagamento vem
    diferente do combinado. WhatsApp fica para a fase 2."""
    destinatario = models.ForeignKey(
        Associado, on_delete=models.CASCADE, related_name='notificacoes',
        verbose_name="Destinatário",
    )
    texto = models.TextField(verbose_name="Texto")
    lida = models.BooleanField(default=False, verbose_name="Lida")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criada em")

    class Meta:
        db_table = "notificacoes"
        ordering = ['-created_at']
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"

    def __str__(self):
        return f"Para {self.destinatario.nome}: {self.texto[:40]}"
