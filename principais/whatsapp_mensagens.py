"""Composição e disparo das mensagens de WhatsApp (lembretes e cobranças).

Mensagens iniciadas por nós usam **templates aprovados** (ver templates_meta/).
Para a equipe (terapeuta/supervisor/gestor) também criamos uma notificação
in-system (decisão #21: in-system + WhatsApp). Pacientes só recebem WhatsApp.

Tudo passa pelo cliente ``principais.whatsapp`` — que é dry-run por padrão e
respeita WHATSAPP_TEST_NUMBER. Nada é enviado de verdade sem configurar o .env.
"""
from principais.models import Associado, Notificacao
from principais.whatsapp import enviar_template

TPL_LEMBRETE_PACIENTE = "lembrete_sessao_paciente"
TPL_LEMBRETE_TERAPEUTA = "lembrete_sessao_terapeuta"
TPL_COBRANCA = "cobranca_pagamento"


def _notificar_associado(associado, texto, template, parametros):
    """Equipe: WhatsApp (template) + notificação in-system."""
    if associado is None:
        return
    Notificacao.objects.create(destinatario=associado, texto=texto)
    if associado.telefone:
        enviar_template(associado.telefone, template, parametros)


# --- Lembrete de sessão (~1h antes) ----------------------------------------
def lembrar_sessao(sessao):
    """Avisa paciente e terapeuta sobre a sessão. ``sessao`` é um SessaoSemanal.
    Retorna o nº de avisos disparados."""
    paciente = sessao.fk_paciente
    terapeuta = paciente.fk_terapeuta
    hora = sessao.hora_inicio.strftime("%H:%M")
    enviados = 0

    # Paciente (só WhatsApp — não é da equipe).
    if paciente.telefone:
        ter_nome = terapeuta.fk_associado.nome if terapeuta else "seu terapeuta"
        enviar_template(paciente.telefone, TPL_LEMBRETE_PACIENTE,
                        [paciente.nome, hora, ter_nome])
        enviados += 1

    # Terapeuta (WhatsApp + in-system).
    if terapeuta:
        assoc = terapeuta.fk_associado
        texto = f"Lembrete: sessão hoje às {hora} com o paciente {paciente.nome}."
        _notificar_associado(assoc, texto, TPL_LEMBRETE_TERAPEUTA,
                             [assoc.nome, hora, paciente.nome])
        enviados += 1
    return enviados


# --- Cobrança de pagamento em atraso ----------------------------------------
def _gestores():
    """Associados de gestores (usuário is_staff)."""
    return list(Associado.objects.filter(usuario__is_staff=True))


def cobrar_atraso(paciente, meses):
    """Dispara a cobrança escalonada para um paciente em atraso:
    >=1 mês -> terapeuta; >=2 -> + supervisor; >=3 -> + gestor(es).
    Retorna o nº de destinatários avisados."""
    terapeuta = paciente.fk_terapeuta
    if terapeuta is None:
        return 0
    texto = (f"O paciente {paciente.nome} está com {meses} mês(es) de pagamento "
             f"em aberto. Verifique e faça a cobrança.")
    destinatarios = []

    # 1 mês: terapeuta.
    destinatarios.append(terapeuta.fk_associado)
    # 2 meses: supervisor.
    if meses >= 2 and terapeuta.fk_supervisor and terapeuta.fk_supervisor.fk_associado_id:
        destinatarios.append(terapeuta.fk_supervisor.fk_associado)
    # 3 meses: gestor(es).
    if meses >= 3:
        destinatarios.extend(_gestores())

    # Dedup por associado.
    vistos, avisados = set(), 0
    for assoc in destinatarios:
        if assoc is None or assoc.pk in vistos:
            continue
        vistos.add(assoc.pk)
        _notificar_associado(assoc, texto, TPL_COBRANCA,
                             [assoc.nome, paciente.nome, str(meses)])
        avisados += 1
    return avisados
