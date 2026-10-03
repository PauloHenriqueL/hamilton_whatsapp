# WhatsApp — guia de configuração (Hamilton 2.0)

O envio usa a **WhatsApp Cloud API da Meta** — o mesmo provedor e o mesmo número
do projeto **Sofia**. O código está em `principais/whatsapp.py` (cliente) e
`principais/whatsapp_mensagens.py` (mensagens). Mensagens que nós iniciamos
(lembrete, cobrança) usam **templates aprovados** (ver `templates_meta/`).

## 1. Credenciais (.env)

Pegue do Sofia (`sofia/render.env`) e coloque no `.env` do Hamilton (e nas env
vars do Render). Mesmo número/WABA do Sofia — enviar não conflita com o webhook
do Sofia.

```
WHATSAPP_TOKEN=<o mesmo WHATSAPP_TOKEN do Sofia>
WHATSAPP_PHONE_NUMBER_ID=<o mesmo WHATSAPP_PHONE_NUMBER_ID do Sofia>
WHATSAPP_DRY_RUN=true          # true = não envia (só loga). Mude p/ false quando testar.
WHATSAPP_TEST_NUMBER=5531983055118   # enquanto preenchido, TUDO vai só p/ este número
```

> Segurança: as credenciais do Sofia estão em texto claro em `sofia/render.env`
> (e podem estar versionadas). Vale **rotacionar** o token da Meta depois.

## 2. Templates na Meta (uma vez, por você)

Os textos estão em `templates_meta/`. No **Gerenciador de Modelos** da Meta
(WhatsApp Manager → Modelos de mensagem) → **Criar modelo**:

Para cada um dos 3 (`lembrete_sessao_paciente`, `lembrete_sessao_terapeuta`,
`cobranca_pagamento`):
1. **Categoria:** Utilidade. **Idioma:** Português (BR).
2. **Nome:** exatamente o do arquivo (minúsculas e `_`).
3. **Corpo:** cole o texto do arquivo (com `{{1}}`, `{{2}}`…).
4. **Exemplos:** preencha os valores de exemplo (a Meta exige).
5. Enviar para aprovação e aguardar ficar **Aprovado**.

⚠️ Crie os templates no **mesmo WhatsApp Business Account do número do Sofia**
(senão o número que envia não "enxerga" o template). O nome tem que bater com o
do código.

### Alternativa: criar via API (sem clicar)

Se preferir não cadastrar à mão, dá para submeter os 3 de uma vez pela
Message Template API. Precisa do **WABA_ID** e de um token com
`whatsapp_business_management`:

```
# veja os payloads que serão enviados:
python manage.py criar_templates_whatsapp
# cria de verdade (precisa WHATSAPP_TOKEN + WHATSAPP_WABA_ID no .env):
WHATSAPP_WABA_ID=<id-do-waba> python manage.py criar_templates_whatsapp --enviar
```

## 3. Cron (agendamento) — no Render

Os disparos no tempo rodam como **Cron Jobs** do Render (Dashboard → New →
**Cron Job**, mesmo repo/imagem do serviço web, mesmas env vars).

### a) Lembretes de sessão (~1h antes)
- **Comando:** `python manage.py enviar_lembretes_sessao`
- **Schedule (a cada 15 min):** `*/15 * * * *`
- A janela padrão é 15 min e casa com essa cadência (cada sessão é avisada uma
  vez, ~1h antes). Se mudar a cadência, passe `--janela <min>` igual.

### b) Cobrança de atrasos (após o OFX, ~dia 10)
- **Comando:** `python manage.py cobrar_atrasos`
- **Schedule (dia 10 às 9h):** `0 9 10 * *`
- Referência = mês passado. Rode **depois** de importar o OFX do mês. Evite
  rodar várias vezes no mesmo dia (cada execução reenvia as cobranças).

> O timezone do servidor pode ser UTC. `enviar_lembretes_sessao` usa o fuso do
> projeto (America/Sao_Paulo) internamente, então o lembrete sai no horário
> local certo. Para o `cobrar_atrasos`, ajuste a hora do cron ao fuso do Render.

## 4. Testar sem incomodar ninguém

1. Deixe `WHATSAPP_DRY_RUN=true` → rode os comandos e veja no log o que *seria*
   enviado, sem enviar nada:
   ```
   python manage.py enviar_lembretes_sessao --simular
   python manage.py cobrar_atrasos --simular
   python manage.py whatsapp_teste --texto "teste"
   ```
2. Para enviar de verdade só para você: `WHATSAPP_DRY_RUN=false` +
   `WHATSAPP_TEST_NUMBER=5531983055118`. Tudo vai para esse número.
3. **Janela de 24h:** texto livre só chega se a pessoa te escreveu nas últimas
   24h. Lembrete/cobrança usam **template**, então chegam a qualquer momento —
   desde que o template esteja **aprovado**. Para testar um texto livre
   (`whatsapp_teste`), mande antes um "oi" do seu WhatsApp para o número da
   clínica (abre a janela de 24h).
