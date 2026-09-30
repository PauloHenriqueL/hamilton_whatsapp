"""
Painel de Notas Fiscais (D18) e download/export (D19).

Adaptado do Hamilton: a nota nasce de ``NotaFiscal`` (que veio da conciliação),
não mais de ``Pagamento``. Emissão individual e em lote, consulta de status,
cancelamento, download de PDF/XML e export de lote (ZIP).
"""
import io
import zipfile
from datetime import date

from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from fiscal.config import ALIQUOTA_ISS_PERCENTUAL, EMITENTE, SERVICO_PADRAO, TEXTO_IMUNIDADE
from fiscal.models import NotaFiscal
from fiscal.services import competencia_mes_anterior, gerar_notas_do_mes
from fiscal.webmania import Webmania


# --------------------------------------------------------------------- emissão
def _montar_nfs_info(nota):
    paciente = nota.fk_paciente
    mes_ref = nota.mes_competencia.strftime('%m/%Y')
    valor = nota.valor or 0
    if valor <= 0:
        valor_servicos, valor_desconto, extra = "0.01", "0.01", \
            " (SERVIÇO GRATUITO/VOLUNTÁRIO - Desconto incondicionado aplicado)"
    else:
        valor_servicos, valor_desconto, extra = f"{valor:.2f}", "0.00", ""

    discriminacao = (
        f"Serviços de psicologia prestados a {paciente.nome}, ref. consultas de "
        f"{mes_ref}. {TEXTO_IMUNIDADE}{extra}"
    )
    nfs_info = {
        "tipo_emissao": "1",
        "emitente": EMITENTE,
        "servico": {
            "data_competencia": nota.mes_competencia.strftime('%Y-%m-%d'),
            "valor_servicos": valor_servicos,
            "desconto_incondicionado": valor_desconto,
            "discriminacao": discriminacao,
            "codigo_servico": SERVICO_PADRAO['codigo'],
            "codigo_nbs": SERVICO_PADRAO['codigo_nbs'],
            "codigo_tributacao_municipio": SERVICO_PADRAO['codigo_tributacao_municipio'],
            "natureza_operacao": SERVICO_PADRAO['natureza_operacao'],
            "tributacao_iss": 4,
            "aliquota_iss": str(ALIQUOTA_ISS_PERCENTUAL),
            "iss_retido": 2,
        },
    }
    if paciente.cpf and str(paciente.cpf).strip():
        nfs_info["tomador"] = {
            "cpf": paciente.cpf, "nome_completo": paciente.nome, "email": paciente.email,
            "cep": paciente.cep, "endereco": paciente.endereco, "numero": paciente.numero,
            "bairro": paciente.bairro, "cidade": paciente.cidade, "uf": paciente.uf,
        }
    return nfs_info


def _emitir_nota(nota, api=None):
    """Emite a NFS-e de uma NotaFiscal. Retorna (ok, mensagem)."""
    paciente = nota.fk_paciente
    if not paciente.tem_cpf:
        nota.status_nfs = NotaFiscal.ERRO
        nota.motivo_erro = "Paciente sem CPF — cadastro incompleto (decisão #4)."
        nota.save(update_fields=['status_nfs', 'motivo_erro', 'updated_at'])
        return False, f"'{paciente.nome}' sem CPF: nota não emitida."

    if api is None:
        api = Webmania()
    resultado = api.send_nfs(_montar_nfs_info(nota))

    if resultado.get('status') in ('aprovado', 'processando'):
        nota.status_nfs = NotaFiscal.PROCESSANDO
        nota.id_nfs = resultado.get('uuid')
        nota.motivo_erro = ''
        nota.save(update_fields=['status_nfs', 'id_nfs', 'motivo_erro', 'updated_at'])
        return True, f"Nota de '{paciente.nome}' enviada para processamento."

    nota.status_nfs = NotaFiscal.ERRO
    erros = resultado.get('log', {}).get('errors', resultado.get('error', str(resultado)))
    nota.motivo_erro = str(erros)
    nota.save(update_fields=['status_nfs', 'motivo_erro', 'updated_at'])
    return False, f"Erro ao emitir nota de '{paciente.nome}': {nota.motivo_erro}"


# ----------------------------------------------------------------------- telas
@staff_member_required
def painel_notas_fiscais(request):
    hoje = date.today()
    mes_param = request.GET.get('mes', '')
    if mes_param:
        try:
            ano, mes = map(int, mes_param.split('-'))
            competencia = date(ano, mes, 1)
        except (ValueError, TypeError):
            competencia = competencia_mes_anterior(hoje)
    else:
        competencia = competencia_mes_anterior(hoje)

    inicio = competencia.replace(day=1)
    fim = (inicio + relativedelta(months=1)) - relativedelta(days=1)

    notas = NotaFiscal.objects.filter(mes_competencia__range=[inicio, fim]).select_related('fk_paciente')
    context = {
        'competencia': inicio,
        'mes_selecionado': inicio.strftime('%Y-%m'),
        'pendentes': notas.filter(status_nfs__in=[NotaFiscal.PENDENTE, NotaFiscal.ERRO]),
        'historico': notas.filter(status_nfs__in=[NotaFiscal.PROCESSANDO, NotaFiscal.EMITIDA, NotaFiscal.CANCELADA]),
    }
    return render(request, 'notas/painel_notas_fiscais.html', context)


@staff_member_required
@require_POST
def fechar_mes(request):
    """Fecha o mês (gera as notas PENDENTE) e já dispara a emissão em lote
    (decisão #14)."""
    mes_param = request.POST.get('mes', '')
    try:
        ano, mes = map(int, mes_param.split('-'))
        competencia = date(ano, mes, 1)
    except (ValueError, TypeError):
        competencia = competencia_mes_anterior(date.today())

    res = gerar_notas_do_mes(competencia)
    msg = (f"Mês {competencia:%m/%Y} fechado: {res.criadas} nota(s) criada(s), "
           f"{res.ja_existiam} já existentes, {res.isentos} isento(s).")
    if res.sem_cpf:
        msg += f" Sem CPF (não emitidas): {', '.join(res.sem_cpf)}."
    messages.success(request, msg)

    # Dispara a emissão em lote das PENDENTE recém-criadas.
    if res.criadas and request.POST.get('emitir') == '1':
        return _emitir_lote(request, competencia)
    return redirect(f"{_painel_url()}?mes={competencia:%Y-%m}")


def _painel_url():
    from django.urls import reverse
    return reverse('painel_notas_fiscais')


def _emitir_lote(request, competencia):
    inicio = competencia.replace(day=1)
    fim = (inicio + relativedelta(months=1)) - relativedelta(days=1)
    pendentes = NotaFiscal.objects.filter(
        mes_competencia__range=[inicio, fim],
        status_nfs__in=[NotaFiscal.PENDENTE, NotaFiscal.ERRO],
    )
    api = Webmania()
    ok = erro = 0
    for nota in pendentes:
        sucesso, _ = _emitir_nota(nota, api=api)
        ok += 1 if sucesso else 0
        erro += 0 if sucesso else 1
    messages.info(request, f"Emissão em lote: {ok} enviada(s), {erro} com erro.")
    return redirect(f"{_painel_url()}?mes={competencia:%Y-%m}")


@staff_member_required
@require_POST
def emitir_nota(request, pk):
    nota = get_object_or_404(NotaFiscal, pk=pk)
    _, msg = _emitir_nota(nota)
    messages.info(request, msg)
    return redirect(f"{_painel_url()}?mes={nota.mes_competencia:%Y-%m}")


@staff_member_required
@require_POST
def emitir_notas_lote(request):
    mes_param = request.POST.get('mes', '')
    try:
        ano, mes = map(int, mes_param.split('-'))
        competencia = date(ano, mes, 1)
    except (ValueError, TypeError):
        competencia = competencia_mes_anterior(date.today())
    return _emitir_lote(request, competencia)


@staff_member_required
@require_POST
def consultar_nota(request, pk):
    nota = get_object_or_404(NotaFiscal, pk=pk)
    if not nota.id_nfs:
        messages.warning(request, "Nota sem UUID para consultar.")
        return redirect(f"{_painel_url()}?mes={nota.mes_competencia:%Y-%m}")
    resultado = Webmania().get_nfs(nota.id_nfs)
    status = (resultado.get('status') or '').lower()
    if status == 'aprovado':
        nota.status_nfs = NotaFiscal.EMITIDA
    elif status == 'cancelado':
        nota.status_nfs = NotaFiscal.CANCELADA
    elif status in ('processando', 'em_processamento'):
        nota.status_nfs = NotaFiscal.PROCESSANDO
    nota.save(update_fields=['status_nfs', 'updated_at'])
    messages.info(request, f"Status de '{nota.fk_paciente.nome}': {nota.get_status_nfs_display()}.")
    return redirect(f"{_painel_url()}?mes={nota.mes_competencia:%Y-%m}")


@staff_member_required
@require_POST
def cancelar_nota(request, pk):
    nota = get_object_or_404(NotaFiscal, pk=pk)
    motivo = request.POST.get('motivo', '').strip() or 'Cancelamento solicitado pela Allos.'
    if not nota.id_nfs:
        messages.warning(request, "Nota sem UUID para cancelar.")
        return redirect(f"{_painel_url()}?mes={nota.mes_competencia:%Y-%m}")
    resultado = Webmania().cancelar_nfs(nota.id_nfs, motivo)
    if resultado.get('status') in ('cancelado', 'aprovado'):
        nota.status_nfs = NotaFiscal.CANCELADA
        nota.motivo_erro = f"Cancelada: {motivo}"
        nota.save(update_fields=['status_nfs', 'motivo_erro', 'updated_at'])
        messages.success(request, f"Nota de '{nota.fk_paciente.nome}' cancelada.")
    else:
        messages.error(request, f"Falha ao cancelar: {resultado}")
    return redirect(f"{_painel_url()}?mes={nota.mes_competencia:%Y-%m}")


# ------------------------------------------------------------------ D19 export
@staff_member_required
def download_pdf_nfs(request, pk):
    nota = get_object_or_404(NotaFiscal, pk=pk)
    conteudo = Webmania().get_nfs_pdf_content(nota.id_nfs) if nota.id_nfs else None
    if not conteudo:
        messages.error(request, "PDF indisponível.")
        return redirect(f"{_painel_url()}?mes={nota.mes_competencia:%Y-%m}")
    resp = HttpResponse(conteudo, content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="nfs_{nota.pk}.pdf"'
    return resp


@staff_member_required
def download_xml_nfs(request, pk):
    nota = get_object_or_404(NotaFiscal, pk=pk)
    conteudo = Webmania().get_nfs_xml_content(nota.id_nfs) if nota.id_nfs else None
    if not conteudo:
        messages.error(request, "XML indisponível.")
        return redirect(f"{_painel_url()}?mes={nota.mes_competencia:%Y-%m}")
    resp = HttpResponse(conteudo, content_type='application/xml')
    resp['Content-Disposition'] = f'attachment; filename="nfs_{nota.pk}.xml"'
    return resp


@staff_member_required
def exportar_notas_lote(request):
    """ZIP com PDF+XML das notas emitidas da competência (D19)."""
    mes_param = request.GET.get('mes', '')
    try:
        ano, mes = map(int, mes_param.split('-'))
        competencia = date(ano, mes, 1)
    except (ValueError, TypeError):
        competencia = competencia_mes_anterior(date.today())
    inicio = competencia.replace(day=1)
    fim = (inicio + relativedelta(months=1)) - relativedelta(days=1)

    notas = NotaFiscal.objects.filter(
        mes_competencia__range=[inicio, fim], status_nfs=NotaFiscal.EMITIDA,
    ).exclude(id_nfs__isnull=True).exclude(id_nfs='')

    buffer = io.BytesIO()
    api = Webmania()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for nota in notas:
            pdf = api.get_nfs_pdf_content(nota.id_nfs)
            xml = api.get_nfs_xml_content(nota.id_nfs)
            base = f"{nota.fk_paciente.nome}_{nota.pk}".replace(' ', '_')
            if pdf:
                zf.writestr(f"{base}.pdf", pdf)
            if xml:
                zf.writestr(f"{base}.xml", xml)
    buffer.seek(0)
    resp = HttpResponse(buffer.getvalue(), content_type='application/zip')
    resp['Content-Disposition'] = f'attachment; filename="notas_{competencia:%Y-%m}.zip"'
    return resp
