# Hamilton 2.0

Reescrita **enxuta** do sistema de gestão da Clínica Allos. O princípio é
simplificar: só se coleta dado que ajuda numa decisão, e **não há cadastro
manual de consulta nem de pagamento** — quem pagou é descoberto **lendo o
extrato bancário (OFX)** e casando o pagador com o paciente.

> Guia completo do projeto: [`CLAUDE.md`](CLAUDE.md). Trabalho dividido em
> partes executáveis: [`demandas.md`](demandas.md).

## Stack

- **Backend:** Django 5.2
- **Banco:** PostgreSQL (Neon) — fallback SQLite em desenvolvimento
- **Deploy:** Render (`build.sh` + `Procfile`)
- **Nota fiscal:** Webmania (NFS-e)
- **Auth:** `User` padrão do Django — gestor (`is_staff`) e terapeuta (não-staff)

## Apps

| App | Responsabilidade |
|-----|------------------|
| `principais` | Associado, Abordagem, Tag, Terapeuta, HorarioDisponivel, Paciente, Notificacao; telas de pacientes, terapeutas, encaminhamento e portal do terapeuta (+ supervisão) |
| `conciliacao` | ExtratoOFX, TransacaoOFX; importação de OFX, matching e fila de pendências |
| `fiscal` | NotaFiscal, config fiscal, cliente Webmania, painel de notas |
| `dashboard` | KPIs (capacidade da equipe e pendências de conciliação) |

## Rodando localmente

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env            # gere uma SECRET_KEY e preencha
./venv/bin/python manage.py migrate
./venv/bin/python manage.py createsuperuser
./venv/bin/python manage.py runserver
```

Sem `DATABASE_URL` no `.env`, roda em SQLite local. As duas áreas:

- **Gestor** (`is_staff`): dashboard, pacientes, terapeutas, encaminhamento,
  conciliação/OFX, notas fiscais.
- **Terapeuta** (não-staff, vinculado via `Associado.usuario`): Meus Horários,
  Meus Pacientes; supervisor usa "ver como" (só-leitura).

## Variáveis de ambiente

Ver [`.env.example`](.env.example). Principais: `SECRET_KEY`, `DEBUG`,
`ALLOWED_HOSTS`, `DATABASE_URL` (Neon do v2), `CSRF_TRUSTED_ORIGINS`,
`WEBMANIA_API_TOKEN`, e `LEGADO_DATABASE_URL` (só no go-live, para a migração).

## Migração do Hamilton antigo

Corte único, executado no **go-live**:

```bash
LEGADO_DATABASE_URL=<neon do hamilton antigo> \
  ./venv/bin/python manage.py migrar_hamilton            # dry-run (padrão)
LEGADO_DATABASE_URL=... ./venv/bin/python manage.py migrar_hamilton --executar
```

Preserva hashes de senha e o vínculo User ↔ Associado ↔ Terapeuta.

## Em construção (fase 2)

Lembretes de sessão por WhatsApp (terapeuta e paciente) e **prontuário por
áudio**: o terapeuta manda um áudio pelo WhatsApp após a sessão e o sistema
gera e guarda o prontuário. Ver [`demandas.md`](demandas.md).
