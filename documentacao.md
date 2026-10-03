# Documentação — Hamilton 2.0 (estado em 03/10/2026)

Resumo do que está entregue, como rodar, e o que falta. Para o plano original
ver `demandas.md`; para as regras do projeto ver `CLAUDE.md`.

---

## 1. Como rodar local

```bash
cd hamilton_alan
venv/bin/python manage.py migrate
venv/bin/python manage.py seed_demo          # dados de demonstração
venv/bin/python manage.py runserver 127.0.0.1:8000
```

- Banco: sem `DATABASE_URL` no `.env`, usa **SQLite** local (`db.sqlite3`).
- **Logins de demonstração** (senha `allos123`):
  - `gestor` — acesso total (is_staff)
  - `ana`, `bruno` (supervisor), `carla` — terapeutas

Testes: `venv/bin/python manage.py test principais` (27 testes).
Testes de navegador (Playwright): scripts em `scratchpad` da sessão.

---

## 2. Variáveis de ambiente (`.env`, gitignored)

| Var | Uso | Estado |
|---|---|---|
| `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` | Django | ✅ configurado local |
| `DATABASE_URL` | Neon (vazio = SQLite) | vazio local |
| `WEBMANIA_API_TOKEN` | NFS-e (Webmania) | ✅ no .env local (conta com assinatura inativa) |
| `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` | envio WhatsApp (conta Sofia) | ✅ no .env local |
| `WHATSAPP_WABA_ID` | criar templates via API | ✅ `2242993489987064` |
| `WHATSAPP_DRY_RUN` | `true`=não envia; `false`=envia | `false` (testando) |
| `WHATSAPP_TEST_NUMBER` | redireciona tudo p/ este número | `5531983055118` |

> As credenciais de produção (Webmania/WhatsApp) são as mesmas do Sofia e do
> Hamilton antigo. Recomendado **rotacionar** (estão em texto claro nos `.env`
> daqueles projetos).

---

## 3. Módulos e estado

| Módulo | App | Estado |
|---|---|---|
| Controle de Pacientes | `principais` | ✅ |
| Controle de Terapeutas (tags, horas, pacientes_max) | `principais` | ✅ |
| Portal do terapeuta: calendário + Meus Pacientes + supervisão | `principais` | ✅ |
| Encaminhamento | `principais` | ✅ |
| OFX / Conciliação | `conciliacao` | ✅ testado com extrato real |
| Nota Fiscal (Webmania) | `fiscal` | ✅ código; 🔴 bloqueado por assinatura Webmania |
| Dashboard (2 KPIs + substitutos) | `dashboard` | ✅ |
| Notificações in-system (sino) | `principais` | ✅ |
| WhatsApp | `principais` | 🟡 envio OK; templates pendentes de aprovação |
| Migração de dados (go-live) | `principais` (`migrar_hamilton`) | comando pronto, roda no go-live |

---

## 4. Horários, capacidade e multi-sessão (novo nesta sessão)

- **Capacidade por horas.** Cada terapeuta tem **15h recomendadas** (não trava).
  `horas_total` = soma dos blocos do calendário. `horas_ocupadas` = nº de
  **sessões** dos pacientes ativos (1h cada) + horas dos blocos de atividade
  (tags). Coluna "Horas x/15" no Controle de Terapeutas; desvio de 15h → aviso.
- **Dois tetos coexistem:** `pacientes_max` (nº de pacientes) **e** as horas.
  Vincular paciente (encaminhamento) checa só `pacientes_max`; a trava de horas
  vale ao **adicionar sessão** no calendário.
- **Tags = atividades.** `HorarioDisponivel.fk_tag`: linha sem tag = disponível
  para paciente; com tag = bloco de atividade (ex.: grupo de estudos). `Tag` tem
  `horas_consumidas` (tempo padrão) + `descricao`.
- **Multi-sessão.** `SessaoSemanal` (fk_paciente, dia_semana, hora_inicio; 1h):
  um paciente pode ter várias sessões/semana. Substituiu o par
  `dia_semana_padrao`/`hora_padrao`. Geridas no calendário (modal "Paciente"
  adiciona; clicar no bloco remove).
- **Calendário (Meus Horários):** grade semanal recorrente estilo Google,
  arrastar-para-criar, modal Bootstrap. Gestor edita o de qualquer terapeuta em
  `/terapeutas/<pk>/horarios/`.
- **Substitutos:** painel no Dashboard — por atividade, quem dá (com dia/hora) e
  quem está apto.
- **Paciente simplificado:** só `is_active` (sem `status_atendimento`).
  "Aguardando encaminhamento" = ativo sem `fk_terapeuta`.

---

## 5. WhatsApp (Cloud API da Meta)

Ver `WHATSAPP_SETUP.md` para o passo a passo completo.

- **Provedor:** mesmo número/conta do **Sofia** — Associação Allos,
  **+55 31 8667-3359**, WABA `2242993489987064`, phone_number_id
  `1095239720349677`.
- **Código:** `principais/whatsapp.py` (cliente), `principais/whatsapp_mensagens.py`
  (lembrete + cobrança), comandos em `principais/management/commands/`.
- **Mensagens:**
  - **Lembrete de sessão** ~1h antes → paciente + terapeuta
    (`enviar_lembretes_sessao`, rodar a cada 15 min).
  - **Cobrança escalonada** de atraso: 1 mês→terapeuta, 2→supervisor, 3→gestor
    (`cobrar_atrasos`, rodar após o OFX; atraso = sem crédito conciliado no mês).
- **Templates (Meta):** 3 criados via API, **PENDENTE de aprovação**:
  `lembrete_sessao_paciente`, `lembrete_sessao_terapeuta`, `cobranca_pagamento`.
  Textos em `templates_meta/`.
- **Modo seguro:** `WHATSAPP_DRY_RUN` e `WHATSAPP_TEST_NUMBER`. Texto livre só
  entrega dentro da janela de 24h; mensagens automáticas usam template aprovado.
- **Status:** envio real **confirmado** (mensagem chegou ao número de teste).
  Falta: aprovação dos templates + cron (no Render, depois).

---

## 6. Nota Fiscal (Webmania)

- **Fluxo:** importar OFX → conciliar → **gestor fecha o mês** (gera NotaFiscal
  PENDENTE por paciente pago) → emitir (individual ou lote) via Webmania →
  baixar PDF/XML / cancelar. Competência = mês do pagamento.
- **Config fiscal** (`fiscal/config.py`): emitente Associação Allos,
  **imunidade / ISS 0%** (Art. 150 VI 'a' CF/88 + ADI 4052/2025). As notas saem
  **sem imposto (imunes)**.
- **Webmania** (`fiscal/webmania.py`): `ambiente=1` = **produção** (nota real);
  `ambiente=2` = homologação (teste).
- 🔴 **BLOQUEIO ATUAL:** a **assinatura da conta Webmania está inativa**
  (`subscription_inactive`). Nenhuma nota emite (real ou teste) até **reativar**
  em https://financeiro.webmaniabr.com/minha-conta/assinatura. O código está
  correto — o payload válido chega na Webmania e autentica; só esbarra na
  assinatura.
- Há uma **nota de teste** pronta (Paulo Henrique Lima, CPF 121.193.416-05,
  R$ 0,01, competência 09/2026, status ERRO=subscription_inactive) para reemitir
  assim que a assinatura voltar.

---

## 7. OFX / Conciliação

- **Importar:** `/conciliacao/importar/` (sobe `.ofx`). Idempotente por hash do
  arquivo e por `fitid`. Só créditos.
- **Conciliar:** por **nome + valor** (`conciliacao/matching.py`). Match → paciente
  conciliado; sem match → fila de "não identificados" (associação manual).
  **Divergência de valor** → flag + notificação in-system ao terapeuta/supervisor.
- **Testado:** importou o extrato real; conciliou (ex.: João Pereira, divergente).
- Arquivo real de exemplo no repo: `extrato-...202609...ofx`.

---

## 8. Comandos úteis (management commands)

```bash
python manage.py seed_demo                 # dados de demonstração
python manage.py whatsapp_teste --numero 5531983055118
python manage.py criar_templates_whatsapp  # dry-run; --enviar cria na Meta
python manage.py enviar_lembretes_sessao --simular
python manage.py cobrar_atrasos --simular
python manage.py migrar_hamilton           # migração do Hamilton antigo (go-live)
```

---

## 9. Pendências / próximos passos

1. 🔴 **Reativar a assinatura da Webmania** → destrava a emissão de NFS-e.
   Depois: refazer o teste de emissão (R$ 0,01) e validar PDF/XML.
2. 🟡 **Aguardar aprovação dos 3 templates** do WhatsApp na Meta.
3. 🟡 **Escrever testes** para `fiscal`, `conciliacao`, `dashboard`.
4. ⚪ **Go-live:** rodar `migrar_hamilton` contra produção + deploy no Render
   (criar os 2 cron jobs do WhatsApp lá). **Só quando decidido** — nada no Render
   por enquanto; tudo é testado local primeiro.
