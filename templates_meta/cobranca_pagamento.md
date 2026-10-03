# Template: cobranca_pagamento

- **name:** `cobranca_pagamento`
- **Categoria:** Utilidade (Utility)
- **Idioma:** Português (BR) — `pt_BR`
- **Enviado para:** o terapeuta (1 mês), o supervisor (2 meses) e o gestor
  (3 meses) — o mesmo texto para os três; muda só quem recebe.

Gatilho: depois que o OFX do mês passado é importado (até ~dia 10). O sistema
sabe quem pagou (crédito conciliado no OFX) e quem não. Para quem não pagou,
dispara a cobrança escalonada por meses em aberto.

## Corpo

```
Olá, {{1}}. O paciente {{2}} está com {{3}} mês(es) de pagamento em aberto.

Por favor, verifique e faça a cobrança. — Clínica Allos
```

## Variáveis

| Var | Significado | Exemplo |
|-----|-------------|---------|
| {{1}} | Nome de quem recebe (terapeuta/supervisor/gestor) | Ana Terapeuta |
| {{2}} | Nome do paciente em atraso | João Pereira |
| {{3}} | Quantidade de meses em aberto | 2 |

## Exemplo renderizado

> Olá, Ana Terapeuta. O paciente João Pereira está com 2 mês(es) de pagamento em aberto.
>
> Por favor, verifique e faça a cobrança. — Clínica Allos
