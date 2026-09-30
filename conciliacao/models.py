"""
Models de conciliação (D12).

Coração do 2.0: o extrato bancário (OFX) é a verdade sobre quem pagou. Cada
arquivo importado vira um ``ExtratoOFX`` (com hash para impedir reimport) e cada
crédito vira uma ``TransacaoOFX`` (com ``fitid`` único para idempotência).
Decisões #10 (idempotência por arquivo + fitid) e #11 (conta única).
"""
from django.db import models

from principais.models import Paciente


class ExtratoOFX(models.Model):
    """Um arquivo OFX importado. O ``hash_arquivo`` único impede reimportar o
    mesmo extrato (decisão #10)."""
    arquivo_nome = models.CharField(max_length=255, verbose_name="Arquivo")
    hash_arquivo = models.CharField(
        max_length=64, unique=True, verbose_name="Hash do arquivo",
        help_text="SHA-256 do conteúdo — barra reimportação duplicada.",
    )
    conta = models.CharField(max_length=50, blank=True, null=True, verbose_name="Conta (ACCTID)")
    data_inicio = models.DateField(blank=True, null=True, verbose_name="Início do período")
    data_fim = models.DateField(blank=True, null=True, verbose_name="Fim do período")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Importado em")

    class Meta:
        db_table = "extratos_ofx"
        ordering = ['-created_at']
        verbose_name = "Extrato OFX"
        verbose_name_plural = "Extratos OFX"

    def __str__(self):
        return f"{self.arquivo_nome} ({self.created_at:%d/%m/%Y})"


class TransacaoOFX(models.Model):
    """Um crédito do extrato. ``fitid`` único garante idempotência (decisão #10)."""
    CONCILIADO = 'CONCILIADO'
    NAO_IDENTIFICADO = 'NAO_IDENTIFICADO'
    STATUS_CHOICES = [
        (CONCILIADO, 'Conciliado'),
        (NAO_IDENTIFICADO, 'Não identificado'),
    ]

    fk_extrato = models.ForeignKey(
        ExtratoOFX, on_delete=models.CASCADE, related_name='transacoes',
        verbose_name="Extrato",
    )
    fitid = models.CharField(
        max_length=100, unique=True, verbose_name="FITID",
        help_text="Identificador único da transação no banco (idempotência).",
    )
    data = models.DateField(verbose_name="Data")
    valor = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Valor")
    nome_pagador = models.CharField(max_length=255, verbose_name="Pagador (cru)")
    nome_normalizado = models.CharField(
        max_length=255, blank=True, default='', verbose_name="Pagador (normalizado)",
        help_text="Sem o prefixo 'Recebimento Pix', sem acentos e em caixa baixa.",
    )
    memo = models.CharField(max_length=255, blank=True, default='', verbose_name="Memo")
    fk_paciente = models.ForeignKey(
        Paciente, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='fk_paciente', verbose_name="Paciente",
    )
    status_conciliacao = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=NAO_IDENTIFICADO,
        verbose_name="Status da conciliação",
    )
    valor_divergente = models.BooleanField(
        default=False, verbose_name="Valor divergente",
        help_text="Casou o paciente, mas o valor difere do combinado (decisão #15).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "transacoes_ofx"
        ordering = ['-data', 'nome_pagador']
        verbose_name = "Transação OFX"
        verbose_name_plural = "Transações OFX"

    def __str__(self):
        return f"{self.data:%d/%m/%Y} · {self.nome_pagador} · R$ {self.valor}"
