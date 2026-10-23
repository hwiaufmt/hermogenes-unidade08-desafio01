# Arquitetura

Visão técnica do **Controle de Materiais de Escritório**: camadas, modelo de dados, fluxo de uma operação e decisões de integridade.

## Camadas

```
Navegador (HTML + JS)  ──fetch──►  routers  ──►  services  ──►  models  ──►  SQLite
```

| Camada | Arquivos | Responsabilidade |
|---|---|---|
| Interface | `app/templates/`, `app/static/` | Renderiza telas e chama a API. **Não calcula saldo nem status.** |
| Routers | `app/routers/` | Recebem HTTP, validam o formato (Pydantic), chamam o service e convertem exceções de domínio em códigos HTTP. **Sem regra de negócio.** |
| Service | `app/services/estoque.py` | Regras de negócio: entrada, saída, status, criação de categoria e material. |
| Dados | `app/models.py`, `app/database.py` | Modelos SQLAlchemy, engine e sessão. |
| Validação | `app/schemas.py`, `app/erros.py` | Schemas de entrada e saída; tradução das mensagens de validação para português. |

### Módulos

- **`main.py`**: cria o app, registra routers, arquivos estáticos e o tratador de erros. No startup cria as tabelas e aplica o seed das categorias.
- **`routers/categorias.py`**: `GET` e `POST /categorias`.
- **`routers/materiais.py`**: `GET /materiais`, `GET /materiais/{id}` e `POST /materiais`.
- **`routers/movimentacoes.py`**: `POST /materiais/{id}/entrada` e `.../saida`.
- **`routers/paginas.py`**: páginas HTML (`/`, `/movimentar`, `/materiais/novo`). Fora da documentação OpenAPI.
- **`erros.py`**: tratador global de `RequestValidationError`. Devolve `422` com `detail` em texto, em português.

## Modelo de dados

```
categorias                 materiais                      movimentacoes
──────────                 ─────────                      ─────────────
id (PK)           ◄──┐     id (PK)              ◄──┐      id (PK)
nome (único)         └──── categoria_id (FK)       └───── material_id (FK)
                           nome                          tipo ('entrada' | 'saida')
                           quantidade (≥ 0)              quantidade (> 0)
                           estoque_minimo (≥ 0)          saldo_apos
                                                         data (UTC)
```

- O **status não é armazenado**: é calculado por `calcular_status(quantidade)` (`0` → "Indisponível", senão "Disponível") e exposto como campo de leitura nas respostas.
- Restrições no banco (`CHECK`): `quantidade >= 0` e `estoque_minimo >= 0` em materiais; `tipo` restrito e `quantidade > 0` em movimentações.
- `movimentacoes` serve para rastreabilidade. Não há tela nem endpoint de histórico no MVP.

## Fluxo de uma saída

1. A tela **Movimentar** envia `POST /materiais/{id}/saida` com `{"quantidade": n}`.
2. O schema `MovimentacaoCriar` exige inteiro estrito maior que zero. Se falhar, `erros.py` devolve `422` em português.
3. O router chama `registrar_saida(db, id, n)`.
4. O service executa **um único `UPDATE`** com a condição de saldo:
   `UPDATE materiais SET quantidade = quantidade - :n WHERE id = :id AND quantidade >= :n RETURNING quantidade`
5. Sem linha afetada: o material não existe (`MaterialInexistenteError` → `404`) ou o saldo é insuficiente (`SaldoInsuficienteError` → `409`). Há `rollback`, então nada é gravado.
6. Com sucesso: grava a `Movimentacao` com o `saldo_apos` e faz `commit`. Saldo e movimentação saem na **mesma transação**.
7. O router devolve o material atualizado, com `quantidade` e `status`.

A entrada segue o mesmo caminho, com `quantidade = quantidade + :n`.

## Decisões de integridade

| Regra | Como é garantida |
|---|---|
| Saldo nunca negativo | Condição `quantidade >= :n` no `UPDATE` e `CHECK` no banco |
| Sem saída dupla concorrente | Verificação e subtração atômicas no mesmo `UPDATE` |
| Tudo ou nada | Saldo e movimentação no mesmo `commit`; `rollback` em qualquer falha |
| Categoria obrigatória e válida | Verificada em `criar_material` antes de gravar |
| Categoria única | Índice único em `categorias.nome`; `IntegrityError` vira `CategoriaDuplicadaError` |
| Quantidade inteira positiva | Validação no schema e, de novo, no service |

## Exceções de domínio

Definidas em `services/estoque.py` e convertidas em HTTP nos routers:

| Exceção | HTTP |
|---|---|
| `CategoriaInexistenteError` | `422` ao cadastrar material; `404` ao filtrar a listagem |
| `CategoriaDuplicadaError` | `422` |
| `MaterialInexistenteError` | `404` |
| `SaldoInsuficienteError` | `409` |
| `QuantidadeInvalidaError` | defesa do service; na API o schema responde antes, com `422` |

## Interface web

Módulos ES, sem framework e sem variáveis globais:

- **`api.js`**: `requisitar`, `enviarJson`, `mostrarMensagem` e a leitura de mensagens de erro da API.
- **`estoque.js`**: carrega categorias e materiais, **agrupa por categoria para exibir** (ordem alfabética) e refaz a consulta ao trocar o filtro.
- **`movimentar.js`**: lista materiais, mostra o saldo vindo da API e registra a movimentação.
- **`cadastro.js`**: cadastra material e cria categoria, atualizando a lista de categorias.

Acessibilidade: HTML semântico, `label` em todo campo, link "Pular para o conteúdo", foco visível, regiões `aria-live` para mensagens, tabelas rolagem-focáveis e selo de status com texto e ícone (não depende só da cor). Alvos de toque de 44px e contraste conferido (campos 4,6:1).

## Testes

`pytest` com `TestClient` e SQLite **em memória** isolado por teste (`tests/conftest.py`).

| Arquivo | Cobre |
|---|---|
| `test_cadastro.py` | CA-01, valores inválidos, filtro por categoria |
| `test_categorias.py` | listar o seed, criar, duplicada, vazia |
| `test_entrada.py` | CA-02 e entradas inválidas |
| `test_saida.py` | CA-03, CA-04 e saídas inválidas |
| `test_estoque.py` | CA-05, CA-06 e registro das movimentações |
| `test_paginas.py` | páginas e arquivos estáticos |
| `test_erros.py` | mensagens de validação em português |
| `test_fluxo_completo.py` | ciclo completo de ponta a ponta |

O JavaScript não tem testes automatizados; foi conferido manualmente no navegador.
