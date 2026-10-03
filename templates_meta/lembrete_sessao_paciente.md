# Template: lembrete_sessao_paciente

- **name:** `lembrete_sessao_paciente`
- **Categoria:** Utilidade (Utility)
- **Idioma:** Português (BR) — `pt_BR`
- **Enviado para:** o paciente, ~1h antes da sessão.

## Corpo

```
Olá, {{1}}! Passando para lembrar da sua sessão hoje às {{2}} com {{3}}.

Se precisar remarcar, fale com a Clínica Allos. Até já!
```

## Variáveis

| Var | Significado | Exemplo |
|-----|-------------|---------|
| {{1}} | Nome do paciente | Mariana Souza |
| {{2}} | Horário da sessão | 14:00 |
| {{3}} | Nome do terapeuta | Ana Terapeuta |

## Exemplo renderizado

> Olá, Mariana Souza! Passando para lembrar da sua sessão hoje às 14:00 com Ana Terapeuta.
>
> Se precisar remarcar, fale com a Clínica Allos. Até já!
