# Demandas — Hamilton 2.0

> Trabalho dividido em **demandas pequenas e auto-contidas**. Cada uma é
> implementável em uma sessão curta. Para tocar o projeto, abra um chat novo e
> peça, por exemplo: *"implemente as demandas D1 a D4"*. Respeite as
> **dependências** — não comece uma demanda antes das que ela exige.
>
> Contexto completo do projeto: ver `CLAUDE.md`. Sistema de referência (a
> copiar/adaptar): `../hamilton-api`.

---

## ✅ Status de entrega (atualizado em 03/10/2026)

**Fases 0–4 (D1–D22): IMPLEMENTADAS.** Todas as telas e módulos do escopo da
fase 1 existem e rodam local (SQLite). App principal = `principais` (não
`cadastros`). Ver `documentacao.md` para o detalhe de cada módulo.

**Fase 5 (D23–D28): IMPLEMENTADA** nesta sessão — sistema de horários por horas,
calendário, multi-sessão, notificações e WhatsApp (ver seção no fim).

**Verificado de verdade (testado):**
- Pacientes, Terapeutas (tags/horas/substitutos), Portal do terapeuta +
  calendário + multi-sessão, Encaminhamento, Dashboard — unit (27 testes) +
  navegador (Playwright).
- **OFX/Conciliação:** ✅ importou o extrato real, conciliou, detectou
  divergência.
- **WhatsApp:** ✅ envio real confirmado (mensagem chegou ao número de teste).

**Pendências (externas/go-live, NÃO são bug de código):**
- 🔴 **Webmania:** assinatura da conta **inativa** → nenhuma NFS-e emite até
  reativar em financeiro.webmaniabr.com. Código da emissão está correto (payload
  válido chega na Webmania).
- 🟡 **WhatsApp:** 3 templates submetidos à Meta, **aguardando aprovação**;
  cron (lembretes/cobranças) a configurar **no Render, depois**.
- 🟡 **Testes** de fiscal/conciliação/dashboard (hoje 0).
- ⚪ **Go-live:** migração real (D6) + deploy Render (D22) — só quando decidir.

## Layout de apps (projeto novo neste diretório)
- `app/` — configuração (settings, urls, wsgi, asgi).
- `cadastros/` — Associado, Abordagem, Tag, Terapeuta, HorarioDisponivel,
  Paciente; telas de Pacientes, Encaminhamento e Terapeutas.
- `conciliacao/` — ExtratoOFX, TransacaoOFX; importação + matching + pendências.
- `fiscal/` — NotaFiscal, config fiscal, `webmania.py` portado, painel de notas.
- `dashboard/` — KPIs (único item "do zero").

> Alternativa: manter o nome `principais` no lugar de `cadastros` reduz fricção
> ao copiar código que faz `from principais.models import ...`. Decisão do
> Alan/Paulo — não bloqueia o plano.

## Blocos de execução sugeridos (~4 por vez)
- **Bloco A:** D1–D4 (fundação)
- **Bloco B:** D5–D8 (models, migração, pacientes, encaminhamento)
- **Bloco C:** D9–D11 (+D11b) (terapeutas, CRUD paciente, portal do terapeuta + supervisão)
- **Bloco D:** D12–D15 (+D14b) (OFX e conciliação)
- **Bloco E:** D16–D19 (notas fiscais)
- **Bloco F:** D20–D22 (dashboard, roteamento, deploy)

---

# FASE 0 — Fundação

## D1 — Bootstrap do projeto Django
- **Objetivo:** esqueleto do projeto Django com as apps vazias.
- **Tocar/criar:** `manage.py`, `app/__init__.py`, `app/settings.py` (mínimo),
  `app/urls.py`, `app/wsgi.py`, `app/asgi.py`, apps `cadastros/`, `conciliacao/`,
  `fiscal/`, `dashboard/`, `requirements.txt` (enxuto: Django, dj-database-url,
  psycopg2-binary, gunicorn, whitenoise, python-dotenv, requests,
  python-dateutil — **sem** stripe/langchain/openai/matplotlib/weasyprint),
  `.gitignore`, `git init`.
- **Pronto quando:** `python manage.py check` passa em SQLite e as 4 apps estão
  em `INSTALLED_APPS`.
- **Depende de:** —

## D2 — Settings Neon/Render + scaffolding de deploy
- **Objetivo:** banco Neon, estáticos e artefatos de deploy do Render.
- **Tocar/criar:** `app/settings.py` (portar de `hamilton-api/app/settings.py`:
  `DATABASE_URL` via urlparse + `sslmode=require`, fallback SQLite; whitenoise +
  `CompressedManifestStaticFilesStorage`; `STATIC_ROOT`; `LANGUAGE_CODE='pt-br'`,
  `TIME_ZONE='America/Sao_Paulo'`; `load_dotenv`; `SECRET_KEY`/`DEBUG`/
  `ALLOWED_HOSTS` por env), `Procfile`
  (`web: gunicorn app.wsgi:application --timeout 300`), `build.sh` (locale pt-BR
  + pip + collectstatic + migrate), `.env.example`.
- **Pronto quando:** `runserver` sobe; `collectstatic` e `migrate` rodam; com o
  `DATABASE_URL` do Neon o `migrate` cria as tabelas default.
- **Depende de:** D1.

## D3 — Design system: base.html, componentes e estáticos
- **Objetivo:** trazer o visual do Hamilton (regra de ouro — parecer o mesmo
  sistema).
- **Tocar/criar:** copiar `app/templates/base.html`, `components/_header.html`,
  `_sidebar.html`, `_view_as_banner.html`, `_footer.html`, `_pagination.html` e
  estáticos (favicon/imagens) do Hamilton. **Adaptar o `_sidebar.html`** para os
  itens do 2.0 conforme o papel: gestor → Dashboard, Controle de Pacientes,
  Controle de Terapeutas, Encaminhamento, Conciliação/OFX, Notas Fiscais;
  terapeuta → Meus Horários, Meus Pacientes (+ seletor de supervisionado). Manter
  o include do `_view_as_banner.html` (usado pela D11b). Remover links de
  consulta/pagamento/plantão/seleção/avaliação/stripe.
- **Pronto quando:** uma página placeholder que estende `base.html` renderiza o
  tema escuro teal com a sidebar correta.
- **Depende de:** D1.

## D4 — Autenticação e papéis (gestor `is_staff` + terapeuta)
- **Objetivo:** login padrão Django + dois papéis (gestor e terapeuta).
- **Tocar/criar:** `app/templates/registration/login.html` (copiar do Hamilton),
  settings `LOGIN_URL`/`LOGIN_REDIRECT_URL`/`LOGOUT_REDIRECT_URL`, mixin
  `StaffRequiredMixin` (portar de `views_controle_terapeutas.py`) em `cadastros/`
  e um mixin/helper para o **terapeuta logado** (resolve o `Terapeuta` a partir
  de `request.user` via `Associado.usuario`).
  - **Gestor (`is_staff`)** → acesso total. **Terapeuta (não-staff)** → só a área
    própria (D11). Redirect pós-login por papel: gestor → dashboard; terapeuta →
    "Meus horários".
- **Pronto quando:** login/logout funcionam; gestor cai no dashboard e terapeuta
  cai na sua área; rota de gestão bloqueada para não-staff.
- **Depende de:** D2, D3. (Decisões #1/#16/#17.)

---

# FASE 1 — Modelos, migração e telas de cadastro

## D5 — Models de cadastro + migração inicial
- **Objetivo:** modelar Associado/Abordagem/Tag/Terapeuta/HorarioDisponivel/
  Paciente no modelo enxuto 2.0.
- **Tocar/criar:** `cadastros/models.py`, `cadastros/admin.py`, migração `0001`.
  - `Associado` (nome, email, telefone, cpf, dat_nascimento, sexo, endereco,
    is_active, OneToOne `usuario→User`). **Remover** setores/faculdade/decano.
  - `Abordagem` (mantida).
  - `Tag` (nome unique + **novo** `horas_consumidas` opcional).
  - `Terapeuta` (`fk_associado`, `fk_abordagem`, `pacientes_max`, `is_active`,
    `observacao`, `tags` M2M, `tags_apto` M2M, **`fk_supervisor` self-FK
    `Terapeuta→Terapeuta` null/blank** — renomeia o antigo `fk_decano`).
    **Remover** fk_nucleo/fk_clinica/fk_modalidade.
  - `HorarioDisponivel` (igual: fk_terapeuta, dia_semana, hora_inicio, hora_fim,
    validate_minutes).
  - `Paciente` (`fk_terapeuta` null/blank = aguardando, nome, telefone, email,
    vlr_sessao, is_active, `status_atendimento`, `origem_paciente`,
    `dia_semana_padrao`, `hora_padrao`, **campo `origem` simples** substituindo
    fk_captacao, e **campos fiscais** cpf/cep/endereco/numero/complemento/
    bairro/cidade/uf). **Remover** fk_clinica/fk_captacao/fk_modalidade/
    tipo_pagamento/stripe.
- **Pronto quando:** `migrate` cria as tabelas e dá para criar objetos no admin.
- **Depende de:** D1. (Decisões travadas #6/#7/#8/#13.)

## D6 — Comando de migração de dados do Hamilton antigo
- **Objetivo:** trazer usuários (com hashes), associados, terapeutas
  (+supervisor) e pacientes (+campos fiscais) num corte único.
- **Tocar/criar:** `cadastros/management/commands/migrar_hamilton.py`
  (referência: `hamilton-api/principais/management/commands/importar_terapeutas.py`).
  - **Users:** preservar `password` (hash) — copiar o campo cru, não
    `set_password`.
  - Mapear `fk_decano → fk_supervisor`; garantir tag `supervisor`; preservar o
    vínculo User↔Associado↔Terapeuta.
  - Pacientes com campos fiscais; captação antiga → campo `origem`.
- **Pronto quando:** o comando existe e roda em dry-run; mapeamentos validados.
  (A execução real contra produção é na **fase final** — ver abaixo.)
- **Depende de:** D5.
- **Fonte (decisão #20):** **conexão direta** ao banco de produção do Hamilton —
  a `DATABASE_URL` do Neon já está em `../hamilton-api/.env`
  (`ep-green-pine-a5wxjxwi...neon.tech/hamiton`). Ler como segundo banco
  (via `DATABASES['legado']`) ou conectar com `psycopg2` direto no comando.
- **Momento:** a migração de dados só é **executada no go-live** (junto de D22).
  Construa o comando agora, mas rode contra produção apenas no fim.
- **Detalhe:** mapear tags `prefeitura`/`supervisor`; preservar hashes de senha.

## D7 — Tela Controle de Pacientes
- **Objetivo:** portar a lista com KPIs/filtros, sem o que saiu do escopo.
- **Tocar/criar:** `cadastros/views.py::ControlePacientesView` (ListView) +
  `cadastros/templates/pacientes/controle_novos_pacientes.html` (copiar do
  Hamilton), `cadastros/forms.py::PacienteFilterForm`, rota `controle-pacientes`.
  - **Manter:** KPIs (novos 30d, capacidade ativos×max), `.fbar`, badge dias sem
    atividade, ações por linha (`.abtn`), paginação.
  - **Remover:** colunas/subqueries de consulta, avaliação inicial/final,
    alta-desistência, Stripe, "1ª sessão pendente"/"sem avaliação". "Dias sem
    atividade" passa a ser dias desde `created_at` (não há mais Consulta).
  - **Adicionar (placeholder até a conciliação):** coluna "pago no mês" e
    "situação fiscal" (CPF ok / sem CPF).
- **Pronto quando:** lista pacientes com filtros, busca e KPIs; ações navegam.
- **Depende de:** D5, D3, D4.

## D8 — Tela Encaminhamento (slots livres + alocação)
- **Objetivo:** portar quase igual o buscador de match com cálculo de slots de
  1h livres.
- **Tocar/criar:** `cadastros/views.py::EncaminhamentoView` +
  `alocar_terapeuta_view` (portar de `principais/views.py` ~3686–3900) +
  `cadastros/templates/pacientes/encaminhamento.html`, rotas.
  - **Aguardando = `fk_terapeuta IS NULL`** (substitui o "sentinela"/id 73 —
    remover toda referência a `sentinela`).
  - Manter filtro nome/abordagem/dia/hora, geração de slots (disponíveis menos
    ocupados por `dia_semana_padrao`/`hora_padrao`), contagem de vagas.
- **Pronto quando:** filtra terapeutas, mostra slots livres agrupados e aloca um
  paciente aguardando via POST.
- **Depende de:** D5, D3, D4. (Tela de gestor — exige o gate `is_staff`.)

---

# FASE 1b — Terapeutas e CRUD de paciente

## D9 — Tela Controle de Terapeutas + APIs de Tag
- **Objetivo:** portar a lista com editor de tags inline e CRUD de tags via JSON.
- **Tocar/criar:** `cadastros/views_controle_terapeutas.py` (portar
  `ControleTerapeutasView`, `TagCreateAPI`, `TagDetailAPI`,
  `TerapeutaTagsAtuaisAPI`, `TerapeutaTagsAptoAPI`, helper `_horarios_agrupados`,
  **+ `TerapeutaMaxAPI`** para editar `pacientes_max` inline via PATCH JSON),
  template `cadastros/templates/controle_terapeutas/lista.html`, rotas JSON.
  - Ajustar imports ao novo `cadastros.models`; supervisor agora é
    `fk_supervisor`.
- **Pronto quando:** painel cria/renomeia/exclui tags, editor inline (atuais +
  apto) salva via API, **o gestor edita o `pacientes_max` de cada terapeuta
  inline (decisão #19)**, horários agrupados por dia e filtro ativo/inativo
  funcionam.
- **Depende de:** D5, D3, D4.

## D10 — CRUD de Paciente (com campos fiscais)
- **Objetivo:** criar/editar/ver/duplicar/inativar paciente, com dados fiscais
  para a NFS-e.
- **Tocar/criar:** `cadastros/views.py` (Create/Update/Detail/Duplicar/Delete),
  `cadastros/forms.py::PacienteForm`, templates `pacientes/paciente_form.html`/
  `paciente_detail.html` (copiar e podar do Hamilton), rotas.
  - Flag visível de "sem CPF" (usada depois pela regra de nota).
- **Pronto quando:** dá para cadastrar/editar um paciente com CPF e endereço
  completos e inativá-lo.
- **Depende de:** D5, D7.

## D11 — Portal do Terapeuta: Meus Horários + Meus Pacientes
- **Objetivo:** o **terapeuta logado** gerencia os próprios `HorarioDisponivel`
  (insumo do Encaminhamento) e **vê os pacientes vinculados a ele** (leitura). O
  gestor também pode editar os horários de qualquer terapeuta.
- **Tocar/criar:** `cadastros/views.py::MeusHorariosView` (edita só os seus,
  resolvidos por `request.user → Associado → Terapeuta`) + `MeusPacientesView`
  (lista `Paciente` com `fk_terapeuta = terapeuta logado`, só-leitura) +
  `GerenciarHorariosView` para o gestor; templates `horarios/meus_horarios.html`
  e `pacientes/meus_pacientes.html` (portar/adaptar do Hamilton), itens no
  `_sidebar.html` só para terapeuta, rotas.
- **Pronto quando:** um terapeuta não-staff loga, vê e edita só seus horários
  (validação 30min) e vê a lista dos seus pacientes; o gestor edita os horários
  de qualquer um.
- **Depende de:** D4, D5, D7. (Decisões #16/#22.)

## D11b — Modo Supervisão ("ver como" supervisionado)
- **Objetivo:** o supervisor vê seus supervisionados e troca a visualização para
  entrar na tela de um deles (pacientes + horários), em **somente leitura**.
- **Tocar/criar:** portar do Hamilton, adaptando `fk_decano/is_decano` para
  `fk_supervisor` + tag `supervisor`:
  - `cadastros/supervisao.py` (sessão `view_as_terapeuta_id`; entrar/voltar;
    restringe aos supervisionados do supervisor: `Terapeuta.filter(
    fk_supervisor=<eu>, is_active=True)`).
  - `cadastros/middleware.py` (bloqueia POST/PUT/PATCH/DELETE enquanto em modo
    supervisão = só-leitura).
  - `cadastros/context_processors.py` (lista `supervisionados` + estado do
    view-as para o seletor no topo).
  - `components/_view_as_banner.html` + o seletor "trocar para supervisionado" no
    header/sidebar; rotas `supervisao_entrar`/`supervisao_voltar`.
  - As views de D11 (Meus Horários/Meus Pacientes) passam a resolver o
    "terapeuta em foco" pelo helper de supervisão (o logado, ou o supervisionado
    em modo view-as).
- **Pronto quando:** um supervisor troca para um supervisionado, vê os pacientes
  e horários dele em leitura, e o banner "voltar à minha visualização" retorna.
- **Depende de:** D11.

---

# FASE 2 — OFX e Conciliação

## D12 — Models de conciliação
- **Objetivo:** modelar extrato e transações com idempotência.
- **Tocar/criar:** `conciliacao/models.py`, admin, migração.
  - `ExtratoOFX`: arquivo, `hash_arquivo` (unique — impede reimport duplicado),
    datas de referência, created_at.
  - `TransacaoOFX`: `fk_extrato`, `fitid` (**unique** — idempotência), `data`,
    `valor`, `nome_pagador`, `memo`, `fk_paciente` (null/blank),
    `status_conciliacao` (`CONCILIADO`/`NAO_IDENTIFICADO`).
- **Pronto quando:** `migrate` cria as tabelas.
- **Depende de:** D5. (Decisões #10/#11.)

## D13 — Importação/parse de OFX
- **Objetivo:** subir o arquivo OFX e gravar créditos sem duplicar.
- **Tocar/criar:** `conciliacao/ofx.py` (parser tolerante a SGML/`<TAG>valor`
  sem fechamento, encoding cp1252), `conciliacao/views.py::ImportarOFXView` +
  template de upload, rota.
  - Só `TRNTYPE=CREDIT`; dedupe por `hash_arquivo` do ExtratoOFX **e** por
    `fitid` da transação.
- **Pronto quando:** subir o `.ofx` real cria as transações de crédito;
  reimportar o mesmo arquivo não duplica nada.
- **Depende de:** D12, D4.
- **Arquivo de exemplo real neste repo:**
  `extrato-conta-corrente-ofx-money_202609_20260901173725.ofx`.
- **Risco:** o `<NAME>` vem como "Recebimento Pix NOME" (prefixo fixo) e às
  vezes truncado; guardar `nome_pagador` cru e também normalizado.

## D14 — Motor de conciliação (nome + valor)
- **Objetivo:** casar cada crédito com um paciente por nome + valor.
- **Tocar/criar:** `conciliacao/matching.py` (normalização: remover prefixo
  "Recebimento Pix", acentos, caixa; comparar com `Paciente.nome`; casar valor
  com `vlr_sessao`), integração acionada na importação e/ou comando `conciliar`.
  - Match único → `CONCILIADO` + `fk_paciente`; sem match ou ambíguo →
    `NAO_IDENTIFICADO`.
  - **Divergência de valor (decisão #15):** se casou o paciente mas o valor do
    crédito ≠ `vlr_sessao` combinado, marcar flag `valor_divergente` na transação
    (a conciliação segue válida; a nota sai pelo valor real). A flag alimenta a
    notificação de D14b.
- **Pronto quando:** após importar, transações com pagador reconhecível ficam
  conciliadas (com flag de divergência quando o valor diverge) e o resto vira
  pendência.
- **Depende de:** D13.
- **Risco:** estratégia de matching (exato vs. fuzzy), truncamento e homônimos.
  Recomendação: começar por match **conservador** (exato normalizado) e mandar o
  resto para a fila manual.

## D14b — Notificação de valor divergente (terapeuta + supervisor)
- **Objetivo:** avisar terapeuta e supervisor quando um pagamento vem divergente
  do combinado (decisão #15). Canal in-system nesta fase (WhatsApp é fase 2).
- **Tocar/criar:** model simples `Notificacao` (destinatário=Associado, texto,
  lida, created_at) em `cadastros/` ou `conciliacao/`; gerar notificações para o
  terapeuta do paciente e seu `fk_supervisor` quando `valor_divergente`; exibir
  na área do terapeuta (D11) e no topo/gestão.
- **Pronto quando:** ao conciliar um crédito divergente, terapeuta e supervisor
  passam a ver uma notificação ao logar.
- **Depende de:** D14, D11.

## D15 — Tela de Conciliação / fila de pendências
- **Objetivo:** o gestor resolve os "não identificados" e vê os conciliados do
  mês.
- **Tocar/criar:** `conciliacao/views.py` (lista pendências + associar paciente
  manualmente + visão de conciliados por mês), template `conciliacao/painel.html`
  (novo, com classes `.tc`/`.sb`), rotas.
  - Alimenta a coluna "pago no mês" do Controle de Pacientes (D7).
- **Pronto quando:** gestor associa um crédito não identificado a um paciente e a
  coluna de pagamento reflete o resultado.
- **Depende de:** D14, D7.

---

# FASE 3 — Notas Fiscais

## D16 — Model NotaFiscal + config fiscal + cliente Webmania
- **Objetivo:** modelar a nota mensal e portar a integração.
- **Tocar/criar:** `fiscal/models.py::NotaFiscal` (`fk_paciente`,
  `mes_competencia`, `valor`, `status_nfs`
  PENDENTE/PROCESSANDO/EMITIDA/ERRO/CANCELADA, `id_nfs` uuid, `motivo_erro`;
  **unique(`fk_paciente`,`mes_competencia`)**), `fiscal/webmania.py` (copiar
  intacto), `fiscal/config.py` (`EMITENTE`, `SERVICO_PADRAO`, `ALIQUOTA_ISS`,
  texto de imunidade — reaproveitar de `acessorios/views.py`), migração.
- **Pronto quando:** tabela criada; `Webmania()` instancia com
  `WEBMANIA_API_TOKEN`.
- **Depende de:** D5, D12. (Decisões #2/#3/#12.)

## D17 — Fechamento do mês → geração de notas
- **Objetivo:** gerar as NotaFiscal PENDENTE a partir da soma real do OFX por
  paciente na competência.
- **Tocar/criar:** `fiscal/services.py::gerar_notas_do_mes(competencia)` +
  acionador (comando `fechar_mes` e/ou botão de gestor), rota.
  - Valor = soma das TransacaoOFX conciliadas do paciente no mês; competência =
    mês anterior.
  - **Pular:** isento (tag `prefeitura`/valor 0) e paciente sem CPF/sem pagador →
    flag na tela do paciente, sem nota.
- **Pronto quando:** fechar um mês cria uma nota PENDENTE por paciente pago,
  ignora isentos e sinaliza os sem CPF.
- **Depende de:** D16, D14.
- **Fluxo (decisão #14):** fechamento **manual**. O gestor entra ~dia 15, escolhe
  o mês anterior e aciona "Fechar mês e emitir" — gera as notas e já dispara a
  emissão em lote (D18). Sem cron/automação.

## D18 — Painel de Notas Fiscais (emitir individual + lote + status/cancelar)
- **Objetivo:** portar o painel adaptando a origem de `Pagamento` para
  `NotaFiscal`.
- **Tocar/criar:** `fiscal/views.py` (`painel_notas_fiscais`, `emitir_nota`,
  `emitir_notas_lote`, `consultar_nota`/`consultar_lote`, `cancelar_nota`;
  `_emitir_nota()` a partir do `_emitir_pagamento` do Hamilton, montando
  `nfs_info` a partir de NotaFiscal+Paciente), template
  `fiscal/templates/notas/painel_notas_fiscais.html` (copiar), rotas.
- **Pronto quando:** emitir individual e em lote por mês, consultar status e
  cancelar com motivo funcionam contra a Webmania.
- **Depende de:** D17.

## D19 — Download e exportação de notas (PDF/XML/ZIP)
- **Objetivo:** baixar documentos e exportar lote.
- **Tocar/criar:** `fiscal/views.py` (`download_pdf_nfs`, `download_xml_nfs`,
  `exportar_notas_lote` — ZIP), rotas; usa `Webmania.get_nfs_pdf_content`/
  `get_nfs_xml_content`.
- **Pronto quando:** baixar PDF/XML de uma nota emitida e exportar um ZIP do mês.
- **Depende de:** D18.

---

# FASE 4 — Dashboard e acabamento

## D20 — Dashboard/KPIs (do zero) — apenas 2 KPIs
- **Objetivo:** tela inicial nova com só os 2 KPIs definidos (decisão #18).
- **Tocar/criar:** `dashboard/views.py::DashboardView` +
  `dashboard/templates/dashboard.html` (novo, usando `.kpi-card`), rota home.
  - **KPI 1 — Capacidade da equipe:** total de pacientes ativos × soma do
    `pacientes_max` de todos os terapeutas (ativos × máximo combinado).
  - **KPI 2 — Pendências de conciliação em aberto:** nº de TransacaoOFX
    `NAO_IDENTIFICADO`.
- **Pronto quando:** home renderiza os 2 KPIs com dados reais.
- **Depende de:** D9, D14.

## D21 — Roteamento final, sidebar e permissões
- **Objetivo:** amarrar navegação e aplicar `is_staff` em todas as telas de
  gestão.
- **Tocar/criar:** `app/urls.py` (incluir todas as apps), revisão do
  `_sidebar.html`, aplicar `StaffRequiredMixin`/`staff_member_required` nas
  views, mensagens/flash.
- **Pronto quando:** navegação completa entre todas as telas e telas de gestão
  bloqueadas para não-staff.
- **Depende de:** D7, D8, D9, D15, D18, D20.
- **Nota:** os gestores (`is_staff`) são Alan, Ari, Tainá, Paulo, Amanda, Victor
  e Arthur — o Alan marca cada um manualmente quando no ar (decisão #17).

## D22 — Deploy no Render
- **Objetivo:** publicar apontando para o Neon e a Webmania.
- **Tocar/criar:** validar `build.sh`/`Procfile`, configurar env no painel do
  Render (`SECRET_KEY`, `DATABASE_URL` Neon, `WEBMANIA_API_TOKEN`, `DEBUG=False`,
  `ALLOWED_HOSTS`), rodar `migrate`/`collectstatic` no build.
- **Pronto quando:** app sobe no Render, login funciona e uma nota de teste é
  emitida no ambiente configurado.
- **Depende de:** D2 + o restante das fases.

---

# FASE 5 — Horários/Capacidade, Notificações e WhatsApp (sessão 03/10/2026)

> Demandas novas, fora do plano D1–D22 original. Todas **implementadas e
> testadas** nesta sessão (salvo pendências externas marcadas).

## D23 — Capacidade por horas + tag como atividade no calendário ✅
- **Entregue:** `Tag` ganhou `descricao`; `horas_consumidas` virou "tempo padrão"
  (duração sugerida). `HorarioDisponivel` ganhou `fk_tag` (bloco de atividade vs
  disponibilidade livre). `Terapeuta` tem `horas_total/ocupadas/livres` e
  `HORAS_RECOMENDADAS=15`. Capacidade = soma dos blocos; ocupado = sessões (1h) +
  horas de tags. Coluna "Horas x/15" no Controle de Terapeutas.
- **Decisão:** 15h é **recomendação** (não trava); desvio gera aviso. Dois tetos
  coexistem: `pacientes_max` (nº) **e** horas.

## D24 — Calendário estilo Google (Meus Horários) ✅
- **Entregue:** grade semanal recorrente (Seg–Dom × horas), arrastar-para-criar
  blocos (disponível / atividade-tag), modal Bootstrap, pacientes em só-leitura.
  API `salvar-horarios`. Gestor edita o de qualquer terapeuta.

## D25 — Painel de Atividades & Substitutos ✅
- **Entregue:** no **Dashboard** (movido do Controle de Terapeutas): por tag,
  quem dá hoje (com dia/hora) e quem está apto a substituir.

## D26 — Multi-sessão por paciente ✅
- **Entregue:** modelo `SessaoSemanal` (1h cada) substitui
  `dia_semana_padrao`/`hora_padrao`. Paciente pode ter várias sessões/semana.
  Capacidade conta sessões. Alocar/remover sessão pelo calendário. `Paciente`
  também perdeu `status_atendimento` (só `is_active`; "aguardando" = ativo sem
  terapeuta).

## D27 — Notificações no sino do header ✅
- **Entregue:** sino com badge vermelho + dropdown (ler / marcar todas como
  lidas), no lugar dos banners que sumiam. Aviso de desvio de 15h com dedupe.

## D28 — WhatsApp (Cloud API da Meta) 🟡 (código pronto; pendências externas)
- **Entregue:** cliente real (`principais/whatsapp.py`, dry-run + modo teste),
  mensagens (`whatsapp_mensagens.py`), comandos `enviar_lembretes_sessao`,
  `cobrar_atrasos`, `whatsapp_teste`, `criar_templates_whatsapp`. Templates em
  `templates_meta/`. Guia em `WHATSAPP_SETUP.md`. **Envio real confirmado.**
- **Regras:** lembrete 1h antes (paciente+terapeuta); cobrança escalonada
  (1 mês→terapeuta, 2→supervisor, 3→gestor); atraso = sem crédito conciliado no
  mês; usa `Associado.telefone` (equipe) / `Paciente.telefone`.
- **Pendente (externo):** templates **aguardando aprovação** da Meta; cron no
  Render (depois). Provedor = mesmo número/conta do Sofia (Associação Allos,
  +55 31 8667-3359, WABA 2242993489987064).

---

## Riscos e decisões (resumo)
- **Único risco técnico aberto — Matching do OFX (D14):** nome com prefixo
  "Recebimento Pix", truncamento e homônimos → começar conservador (match exato
  normalizado) + fila manual.

### Resolvido
- Fechamento do mês (D17): **manual**, gestor ~dia 15 fecha o mês anterior.
- Valor divergente (D14/D14b): emite pelo valor real + flag + notifica terapeuta
  e supervisor (in-system e/ou WhatsApp; começa in-system).
- `is_staff` (D21): Alan, Ari, Tainá, Paulo, Amanda, Victor, Arthur — Alan marca
  manualmente quando no ar.
- Login do terapeuta para informar horários (D4/D11).
- Dashboard (D20): só 2 KPIs — capacidade da equipe e pendências de conciliação.
- Gestor edita `pacientes_max` na tela de terapeutas (D9).
- Migração (D6): conexão direta ao banco de produção, executada no go-live.

## Arquivos de referência mais críticos (Hamilton antigo)
- `../hamilton-api/principais/models.py`
- `../hamilton-api/principais/views.py` (ControleNovosPacientesView ~3410,
  EncaminhamentoView ~3686)
- `../hamilton-api/principais/views_controle_terapeutas.py`
- `../hamilton-api/acessorios/views.py` e `../hamilton-api/acessorios/webmania.py`
- `../hamilton-api/app/settings.py` e `../hamilton-api/app/templates/base.html`
  (+ `components/_sidebar.html`, `_header.html`)
- OFX de exemplo: `extrato-conta-corrente-ofx-money_202609_20260901173725.ofx`
