# Hamilton 2.0 — Guia do Projeto

> Documento-fonte para qualquer sessão de IA ou dev que for trabalhar neste
> repositório. Lê isto **antes** de escrever qualquer código. As demandas
> executáveis (o trabalho dividido em partes pequenas) estão em `demandas.md`.

---

## 1. O que é este projeto

O **Hamilton 2.0** é uma reescrita **enxuta** do sistema de gestão da Clínica
Allos (o "Hamilton" original, em `../hamilton-api`). O objetivo é simplificar
radicalmente: manter só o que ajuda uma decisão e eliminar cadastro manual.

A grande mudança em relação ao Hamilton atual: **não há cadastro de consulta
nem de pagamento**. Quem pagou passa a ser descoberto **lendo o extrato
bancário (OFX)** e casando o nome do pagador com o paciente. Com isso o sistema
sabe que "o paciente X, do terapeuta Y, pagou" — e emite a nota fiscal do mês.

### Os três princípios (do Paulo, na reunião de 30/09/2026)
1. **Simplificar** — dado que não ajuda numa decisão não é coletado.
2. **Mínima fricção** — no dia a dia quase tudo deveria ser WhatsApp (fase 2).
3. **Dado forte** — não se pergunta "pagou?"; olha-se o extrato. O extrato é a
   verdade e nunca é confrontado com palpite.

---

## 2. Stack e infraestrutura

- **Backend:** Django (mesma base do Hamilton atual).
- **Banco:** PostgreSQL no **Neon**.
- **Deploy:** **Render** (`build.sh` + `Procfile`, como no Hamilton).
- **Nota fiscal:** **Webmania** (NFS-e) — cliente já existe em
  `../hamilton-api/acessorios/webmania.py` e deve ser portado quase intacto.
- **Auth / papéis:** `User` padrão do Django (sem modelo custom). Dois papéis:
  - **Gestor = `is_staff`** — acesso total (telas de gestão, OFX, notas).
  - **Terapeuta = usuário não-staff** vinculado (via `Associado.usuario →
    Terapeuta`) — área própria onde: **informa os próprios horários
    disponíveis** (`HorarioDisponivel`, insumo do Encaminhamento) e **vê os
    pacientes vinculados a ele** (somente leitura).
  - **Supervisor** (terapeuta com supervisionados / tag `supervisor`) — além do
    próprio portal, vê a lista dos **seus supervisionados** e pode **trocar a
    visualização** ("ver como") para entrar na tela de um supervisionado e ver os
    **pacientes e horários** daquela pessoa, em **somente leitura**. Já existe no
    Hamilton: portar `principais/supervisao.py` (sessão `view_as_terapeuta_id`),
    `principais/middleware.py` (bloqueia escrita no modo supervisão),
    `principais/context_processors.py` (lista de supervisionados) e
    `components/_view_as_banner.html`, adaptando `fk_decano/is_decano` para
    `fk_supervisor` + tag `supervisor`.

---

## 3. REGRA DE OURO — Templates e visual

**O Hamilton 2.0 tem que parecer apenas mais uma tela do Hamilton.** Não se
inventa design novo. Regras obrigatórias:

- **Estender o `base.html` do Hamilton** (`../hamilton-api/app/templates/base.html`).
  Copiar o `base.html`, os componentes (`components/_header.html`,
  `_sidebar.html`) e o design system para este projeto e manter as mesmas
  variáveis de cor e classes.
- **Design system:** Bootstrap 5.3.3 + Bootstrap Icons + Font Awesome. Fontes
  **DM Sans** (corpo) / **Fraunces** (display). Tema escuro via
  `body.theme-dark`. Paleta teal: `--teal-500:#2E9E8F`, `--bg-page:#0F1419`,
  `--bg-card:#151C24`, `--text-primary:#E8ECF0`, além dos tokens
  `--green/amber/red-*` para status.
- **Reusar as classes de componente já existentes**: `.pg-h` (cabeçalho de
  página), `.fbar` (barra de filtros), `.tc` (tabela em card), `.kpi-card`,
  `.sb`/`.sb-ok`/`.sb-warn`/`.sb-bad`/`.sb-info`/`.sb-muted` (badges de status),
  `.btn-pri`, `.abtn` (ações por linha), `.av` (avatar).
- **Copiar as telas do Hamilton como ponto de partida**, adaptando ao modelo
  2.0 — ver a seção 6. Não recriar do zero o que já existe e já foi aprovado
  pelos usuários. O único item "do zero" é o **dashboard/KPIs**.

> Nota: o protótipo em HTML flat (mostrado ao cliente) serviu só para validar
> **fluxo**. O sistema real segue o visual do Hamilton descrito acima, não o
> protótipo.

---

## 4. Escopo

### Entra (fase 1)
- Migração dos dados do Hamilton atual (usuários, terapeutas, pacientes).
- **Controle de Pacientes** (com Encaminhamento).
- **Controle de Terapeutas** (com criação/edição de tags inline + edição do
  `pacientes_max`).
- **Portal do Terapeuta** — Meus Horários (edita) + Meus Pacientes (leitura); e
  o **modo supervisão** ("ver como" supervisionado, só-leitura).
- **Importação de OFX** + conciliação (nome + valor) + fila de pendências +
  notificação de divergência.
- **Notas Fiscais** mensais via Webmania (emitir, baixar PDF/XML, cancelar,
  lote).
- **Dashboard** novo (do zero) com **2 KPIs** — ver seção 6.

### Fica de fora (fase 2 ou descartado)
- Cadastro manual de consulta e de pagamento (substituídos pelo OFX).
- Automação por WhatsApp, prontuário por áudio, IA Sofia, plantão.
- Stripe/assinaturas, processo seletivo, avaliações, contratos.
- Tabelas de apoio: **clínica, modalidade e núcleo somem**; **captação** vira um
  campo simples de origem no paciente; **abordagem** permanece como tabela.

---

## 5. Modelo de dados

### Tabelas que vêm do Hamilton (migradas / adaptadas)
- **User** (Django) — login; **hashes de senha preservados** na migração.
- **Associado** — dados da pessoa (nome, telefone, CPF, e-mail, etc.) + vínculo
  1-1 com `User`. Base de terapeutas, supervisores e gestores. **Mantida.**
- **Terapeuta** — `fk_associado`, `pacientes_max`, `is_active`, `observacao`,
  `fk_abordagem`, `tags` (M2M) e `tags_apto` (M2M). **Supervisor:**
  auto-relacionamento `fk_supervisor → Terapeuta` (renomeado do antigo
  `fk_decano`); o supervisor também é terapeuta e carrega a tag `supervisor`.
- **Paciente** — `fk_terapeuta` (nullable p/ quem aguarda), `nome`, `telefone`,
  `email`, `vlr_sessao`, `is_active`, `status_atendimento`, `origem_paciente`
  (NOVO/REENCAMINHADO), `dia_semana_padrao`, `hora_padrao`, e os **campos
  fiscais** exigidos pela NFS-e: `cpf`, `cep`, `endereco`, `numero`, `bairro`,
  `cidade`, `uf`.
- **Tag** — `nome` + **campo novo `horas_consumidas`** (opcional; ex.: palestra
  consome X horas do terapeuta).
- **HorarioDisponivel** — `fk_terapeuta`, `dia_semana`, `hora_inicio`,
  `hora_fim`.
- **Abordagem** — mantida.

### Tabelas novas (coração do 2.0)
- **ExtratoOFX** — cada arquivo importado (conta única). Guarda hash/identidade
  do arquivo para **impedir importação duplicada**.
- **TransacaoOFX** — cada crédito do extrato: `fitid` (único, idempotência),
  `data`, `valor`, `nome_pagador`, `fk_paciente` (nullable),
  `status_conciliacao` (conciliado / não identificado).
- **NotaFiscal** — **uma por paciente por mês**: `fk_paciente`,
  `mes_competencia`, `valor`, `status_nfs`
  (PENDENTE/PROCESSANDO/EMITIDA/ERRO/CANCELADA), `id_nfs` (uuid Webmania),
  `motivo_erro`. (No Hamilton esses campos viviam no `Pagamento`; aqui nascem da
  conciliação.)
- **Config fiscal** — emitente, código de serviço, ISS, texto de imunidade.
  Reaproveitar os valores já usados no Hamilton (mesmo CNPJ/regras da Allos).

---

## 6. Telas — herdar do Hamilton, adaptar ao 2.0

Referências no Hamilton (`../hamilton-api`):

- **Controle de Pacientes** — `principais/templates/pacientes/controle_novos_pacientes.html`
  + `ControleNovosPacientesView`. Mantém: KPIs, barra de filtros, badge de
  "dias sem atividade", ações por linha (ver/editar/duplicar/inativar/alocar),
  modal de alocação, paginação. **Remove** colunas de consulta/avaliação/Stripe;
  **adiciona** coluna de pagamento (vindo do OFX) e situação fiscal (CPF ok / sem
  CPF).
- **Encaminhamento** — `pacientes/encaminhamento.html` + `EncaminhamentoView`.
  Buscador de match: filtra terapeutas por nome/abordagem/dia/hora e **calcula os
  slots de 1h livres** (horários disponíveis menos os já ocupados por
  `dia_semana_padrao`/`hora_padrao`). Aloca paciente aguardando. **Portar
  praticamente igual.**
- **Controle de Terapeutas** — `controle_terapeutas/lista.html` +
  `views_controle_terapeutas.py`. Mantém: painel de **criar/renomear/excluir
  tags** e **editor de tags inline** (atuais + "apto a") via APIs JSON; filtros;
  horários agrupados por dia; ativo/inativo. **Novo:** o gestor pode **editar o
  `pacientes_max`** (máximo de pacientes) de cada terapeuta nesta tela. **Portar
  quase igual + edição do máximo.**
- **Notas Fiscais** — `acessorios/templates/notas/painel_notas_fiscais.html` +
  `acessorios/views.py` + `acessorios/webmania.py`. Mantém: emitir individual,
  **emitir em lote por mês**, **exportar lote (ZIP de PDF/XML)**, pendentes,
  histórico com **download PDF/XML**, **cancelar** com motivo, consultar status.
  **Muda a origem:** a nota nasce da conciliação do OFX, não de um `Pagamento`.
- **Dashboard** — **novo, do zero.** Apenas **2 KPIs**:
  1. **Capacidade da equipe** = total de pacientes ativos × soma do
     `pacientes_max` de todos os terapeutas (ativos × máximo combinado).
  2. **Pendências de conciliação em aberto** (créditos não identificados).

---

## 7. Regras de negócio — conciliação e nota fiscal

- **Conta única:** um só extrato alimenta o sistema.
- **Um Pix por paciente por mês:** cada paciente combina um valor e manda um
  único Pix. Conciliação por **nome + valor**.
- **Não bateu → flag:** crédito sem paciente correspondente recebe uma flag de
  "não identificado" e aparece para o gestor resolver na tela.
- **Idempotência:** guardar o OFX no banco e usar o `fitid` de cada transação
  para nunca duplicar crédito nem nota ao reimportar.
- **Competência = mês anterior.** A nota só é emitida **depois que o mês fecha**.
- **Valor da nota = soma real do OFX** (dado forte), mesmo que divirja do
  combinado.
- **Valor divergente do combinado:** emite mesmo assim pelo valor real, **mas
  levanta uma flag de divergência e notifica o terapeuta e o supervisor**. A
  notificação começa **in-system** (aparece quando logam); pode ser **também por
  WhatsApp** — sem bloqueio (decisão #21).
- **Sem pagador/sem CPF → não emite.** Fica flag para o gestor completar o
  cadastro (tela do paciente).
- **Isento não gera nota:** paciente com tag `prefeitura` tem `vlr_sessao = 0` e
  não paga.

---

## 8. Migração (corte único)

- Trazer **todos os usuários**, **preservando os hashes** de senha.
- Preservar o vínculo **User ↔ Associado ↔ Terapeuta** e o vínculo de
  **supervisor**.
- Trazer pacientes **com os campos fiscais**.
- Sem backfill de OFX: começa do zero (sem notas retroativas).
- É uma migração **única** (migra e desliga o Hamilton antigo); não precisa de
  re-sincronização.
- **Fonte:** conexão direta ao banco de produção do Hamilton. A `DATABASE_URL`
  do Neon já existe em `../hamilton-api/.env`
  (`ep-green-pine-a5wxjxwi...neon.tech/hamiton`).
- **Momento:** a migração roda **na parte final do projeto** (go-live). O comando
  é construído cedo (D6), mas só é executado no fim, contra produção.

---

## 9. Decisões travadas

| # | Decisão |
|---|---------|
| 1 | Gestor = `is_staff` do Django (sem tabela de papel nova). |
| 2 | Nota **mensal**, competência do mês anterior. |
| 3 | Valor da nota = soma real do OFX. |
| 4 | Sem pagador/CPF → não emite; vira flag na tela do paciente. |
| 5 | Isento (tag `prefeitura`, valor 0) não gera nota. |
| 6 | `Associado` mantido (dados da pessoa + vínculo com User). |
| 7 | Supervisor = auto-relação `Terapeuta→Terapeuta` + tag `supervisor`. |
| 8 | `Tag` ganha campo opcional `horas_consumidas`. |
| 9 | Sem backfill histórico de OFX — começa do zero. |
| 10 | Idempotência do OFX pelo arquivo salvo + `fitid`. |
| 11 | Uma conta bancária só. |
| 12 | Regras fiscais reaproveitadas do Hamilton atual. |
| 13 | Clínica, modalidade e núcleo somem; abordagem fica; captação vira campo. |
| 14 | **Fechamento manual**: o gestor entra ~dia 15 e fecha o mês anterior, emitindo todas as notas de uma vez. Sem automação/cron. |
| 15 | **Valor divergente** (~~original~~ **revisada por #25**): emite pelo valor real do OFX. (Antes: flag + notifica terapeuta e supervisor em qualquer diferença.) |
| 16 | **Terapeuta tem login próprio** (não-staff) para informar os horários disponíveis. |
| 17 | Gestores (`is_staff`): Alan, Ari, Tainá, Paulo, Amanda, Victor, Arthur. São usuários que já existem no Hamilton; o Alan marca/confere o `is_staff` de cada um manualmente quando o sistema estiver no ar. |
| 18 | Dashboard tem **só 2 KPIs**: capacidade da equipe (ativos × máximo combinado) e pendências de conciliação em aberto. |
| 19 | Gestor edita o `pacientes_max` de cada terapeuta na tela de Controle de Terapeutas. |
| 20 | Migração por **conexão direta** ao banco de produção (`DATABASE_URL` em `../hamilton-api/.env`), executada **na fase final** (go-live). |
| 21 | Notificação de divergência pode ser **in-system e/ou WhatsApp** — sem bloqueio; começa in-system. |
| 22 | Portal do terapeuta: **Meus Horários** + **Meus Pacientes** (leitura). Supervisor vê seus supervisionados e usa "**ver como**" (só-leitura) para entrar na tela de um supervisionado. Portar o mecanismo de supervisão do Hamilton. |
| 23 | **Pagadores alternativos**: o paciente pode ter vários nomes de quem paga o Pix (mãe/pai etc.), em tabela `PagadorAlternativo`. A conciliação tenta o nome do próprio paciente e, só se não casar, os pagadores. Associação manual aprende o nome automaticamente. Estende #7. |
| 24 | **Data do 1º pagamento** no paciente (campo `data_primeiro_pagamento`): só **expectativa** do dia recorrente do Pix (deriva `dia_pagamento_esperado`), nunca prova — respeita #3. Usada para indicador de **atraso** na tela (sem crédito conciliado no mês após o dia esperado + carência de 5 dias). |
| 25 | **Alerta de pagamento abaixo do mínimo** (revisa #15): valor esperado é **global** (faixa R$200–250). Crédito conciliado **< R$200** → alerta **só ao terapeuta** (in-system) para negociar o valor na faixa. ≥ R$200 (inclusive acima de 250) não alerta. Isento (`vlr_sessao 0`) nunca alerta. Nota sai pelo valor real (#3 intacta). |

## 10. Perguntas em aberto

Nenhuma bloqueante. Escopo fechado para iniciar a implementação.

---

## 11. Referências

- Hamilton atual: `../hamilton-api` (Django + templates + Webmania).
- Reunião que originou o projeto: `reunião_alan.md`.
- Requisitos brutos do cliente: `Duvidas.xlsx`.
- Trabalho dividido em partes executáveis: `demandas.md`.
