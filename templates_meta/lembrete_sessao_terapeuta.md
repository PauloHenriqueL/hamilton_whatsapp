# Template: lembrete_sessao_terapeuta

- **name:** `lembrete_sessao_terapeuta`
- **Categoria:** Utilidade (Utility)
- **Idioma:** Português (BR) — `pt_BR`
- **Enviado para:** o terapeuta, ~1h antes da sessão.

## Corpo

```
Olá, {{1}}! Lembrete: você tem sessão hoje às {{2}} com o paciente {{3}}. Bom atendimento!
```

> Nota: a Meta não permite variável no início/fim do corpo — por isso o
> "Bom atendimento!" no fim.

## Variáveis

| Var | Significado | Exemplo |
|-----|-------------|---------|
| {{1}} | Nome do terapeuta | Ana Terapeuta |
| {{2}} | Horário da sessão | 14:00 |
| {{3}} | Nome do paciente | Mariana Souza |

## Exemplo renderizado

> Olá, Ana Terapeuta! Lembrete: você tem sessão hoje às 14:00 com o paciente Mariana Souza.
