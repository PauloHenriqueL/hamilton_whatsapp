"""
Configuração fiscal (D16). Reaproveitada do Hamilton (decisão #12): mesmo
CNPJ/regras da Allos, serviço de psicologia com imunidade (ISS 0).
"""
from decimal import Decimal

EMITENTE = {
    "cnpj": "50990346000152",
    "inscricao_municipal": "1479133001X",
    "razao_social": "ASSOCIACAO ALLOS",
    "nome_fantasia": "Allos",
    "endereco": {
        "cep": "30431058", "logradouro": "R Rio Negro", "numero": "1048",
        "bairro": "Barroca", "cidade": "Belo Horizonte", "uf": "MG",
    },
    "telefone": "31993147985",
    "email": "diretoria@allos.org.br",
}

SERVICO_PADRAO = {
    "codigo": "041601",
    "codigo_tributacao_municipio": "416",
    "natureza_operacao": 4,
    "codigo_nbs": "1.2301.98.00",
}

ALIQUOTA_ISS_PERCENTUAL = Decimal('0.0')

TEXTO_IMUNIDADE = (
    "Imunidade conforme Art. 150, VI, 'a' da CF/88 e conforme Ato Declaratório "
    "de Imunidade - ADI N° 4052/2025. Processo Administrativo nº "
    "31.00838515/2025-35."
)
