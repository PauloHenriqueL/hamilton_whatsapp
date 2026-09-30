"""
NotaFiscal (D16): uma nota por paciente por mês de competência.

No Hamilton esses campos viviam no ``Pagamento``; aqui a nota nasce da
conciliação do OFX (decisões #2/#3). Competência = mês anterior (decisão #2);
valor = soma real do OFX conciliado (decisão #3).
"""
from django.db import models

from principais.models import Paciente


class NotaFiscal(models.Model):
    PENDENTE = 'PENDENTE'
    PROCESSANDO = 'PROCESSANDO'
    EMITIDA = 'EMITIDA'
    ERRO = 'ERRO'
    CANCELADA = 'CANCELADA'
    STATUS_CHOICES = [
        (PENDENTE, 'Pendente'),
        (PROCESSANDO, 'Processando'),
        (EMITIDA, 'Emitida'),
        (ERRO, 'Erro'),
        (CANCELADA, 'Cancelada'),
    ]

    fk_paciente = models.ForeignKey(
        Paciente, on_delete=models.PROTECT, db_column='fk_paciente',
        related_name='notas', verbose_name="Paciente",
    )
    mes_competencia = models.DateField(
        verbose_name="Competência",
        help_text="Primeiro dia do mês de competência (mês anterior ao fechamento).",
    )
    valor = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Valor")
    status_nfs = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=PENDENTE,
        verbose_name="Status da NFS-e",
    )
    id_nfs = models.CharField(
        max_length=64, blank=True, null=True, verbose_name="UUID Webmania",
    )
    motivo_erro = models.TextField(blank=True, default='', verbose_name="Motivo do erro")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notas_fiscais"
        ordering = ['-mes_competencia', 'fk_paciente__nome']
        verbose_name = "Nota Fiscal"
        verbose_name_plural = "Notas Fiscais"
        # Uma nota por paciente por mês (idempotência do fechamento).
        unique_together = ('fk_paciente', 'mes_competencia')

    def __str__(self):
        return f"NF {self.fk_paciente.nome} · {self.mes_competencia:%m/%Y} · {self.status_nfs}"
