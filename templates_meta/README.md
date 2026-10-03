# Templates de WhatsApp (Meta) — Hamilton 2.0

Mensagens que **nós iniciamos** (lembrete de sessão, cobrança) são enviadas
**fora da janela de 24h** da Meta, então **exigem templates aprovados** na
WhatsApp Cloud API. Texto livre só funciona nas 24h após a pessoa nos escrever.

## Como submeter (uma vez, por você)

1. Entre no **Meta Business Manager** → **WhatsApp Manager** → **Modelos de
   mensagem** (Message Templates), na mesma conta/número do projeto **Sofia**.
2. Clique em **Criar modelo**.
3. Para cada template abaixo, preencha:
   - **Nome**: exatamente o `name` indicado (minúsculas e `_`).
   - **Categoria**: **Utilidade** (Utility) — são mensagens transacionais.
   - **Idioma**: **Português (BR)** → código `pt_BR`.
   - **Corpo**: copie o texto do campo *Corpo*, com as variáveis `{{1}}`, `{{2}}`…
   - **Exemplos**: use os valores de *Exemplo* (a Meta exige exemplo de cada variável).
4. Envie para aprovação. A Meta revisa (minutos a ~1 dia). Status fica **Aprovado**.
5. Quando aprovados, o código já usa esses nomes — nada a mudar.

> Os `name`, a ordem e a quantidade de variáveis **têm que bater** com o que o
> código envia (ver `principais/whatsapp_mensagens.py`). Se você mudar o texto,
> mantenha a mesma quantidade/ordem de variáveis.

## Lista

| Arquivo | `name` | Para quem | Variáveis |
|---|---|---|---|
| `lembrete_sessao_paciente.md` | `lembrete_sessao_paciente` | Paciente | nome, hora, terapeuta |
| `lembrete_sessao_terapeuta.md` | `lembrete_sessao_terapeuta` | Terapeuta | nome, hora, paciente |
| `cobranca_pagamento.md` | `cobranca_pagamento` | Terapeuta/Supervisor/Gestor | nome, paciente, meses |
