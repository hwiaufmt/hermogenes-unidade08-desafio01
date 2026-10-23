# Controle de Materiais de Escritório

Aplicação web para controlar o estoque de materiais de escritório (papelaria, escrita, informática etc.): cadastrar materiais por categoria, registrar entradas e saídas e consultar o saldo atualizado.

Este é um **MVP** que valida o ciclo *cadastrar → entrada → saída → consultar saldo*, com regras de negócio confiáveis.

## Funcionalidades

- **Categorias:** seed inicial (Papelaria, Escrita, Informática) e criação de novas pela interface.
- **Cadastro de material:** exige categoria válida; estoque inicial e estoque mínimo opcionais (padrão 0).
- **Entrada e saída:** a entrada soma ao saldo; a saída subtrai e é **bloqueada** se o saldo for insuficiente.
- **Status automático:** saldo 0 → **Indisponível**; qualquer outro → **Disponível**. Não há campo editável.
- **Estoque:** materiais e saldos agrupados por categoria, com filtro.
- Cada entrada e saída grava uma movimentação (tipo, quantidade, saldo após, data UTC) na mesma transação do saldo.

## Stack

Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2 com SQLite, Jinja2, HTML/CSS/JavaScript (ES modules, sem framework), pytest + httpx e ruff.

## Como rodar

Requer Python 3.11 ou superior.

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Linux/macOS:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Com o ambiente ativo:

```bash
uvicorn app.main:app --reload
```

Abra <http://localhost:8000>. A documentação interativa da API fica em `/docs`.
O banco é o arquivo `estoque.db`, criado na raiz ao iniciar, junto com o seed das categorias.

## Como testar

```bash
pytest                          # testes (usam SQLite em memória)
ruff check . && ruff format .   # lint e formatação
```

Cada critério de aceite tem testes nomeados com o ID (`test_ca01_...` a `test_ca06_...`).

## Páginas

| Rota | Descrição |
|---|---|
| `/` | **Estoque:** saldos agrupados por categoria, com filtro |
| `/movimentar` | **Movimentar:** registrar entrada ou saída e ver o saldo |
| `/materiais/novo` | **Cadastro:** novo material e nova categoria |

## API

| Método e rota | Descrição | Erros |
|---|---|---|
| `GET /categorias` | Lista as categorias | |
| `POST /categorias` | Cria categoria (`nome` único) | `422` vazio ou duplicado |
| `GET /materiais` | Lista materiais; filtro `?categoria_id=` | `404` categoria inexistente |
| `GET /materiais/{id}` | Consulta um material | `404` |
| `POST /materiais` | Cadastra material | `422` categoria ausente/inválida, valores inválidos |
| `POST /materiais/{id}/entrada` | Soma `quantidade` ao saldo | `404`, `422` |
| `POST /materiais/{id}/saida` | Subtrai `quantidade` do saldo | `404`, `422`, `409` saldo insuficiente |

Entrada e saída recebem `{"quantidade": n}` (inteiro maior que zero) e devolvem o material atualizado, com `quantidade` e `status`. Todas as mensagens de erro, inclusive as de validação (`422`), vêm em português no campo `detail`, como texto.

## Regras de negócio

- Quantidade de entrada e saída: inteiro maior que zero.
- O saldo nunca fica negativo.
- A verificação de saldo e a subtração na saída são **atômicas** (`UPDATE ... WHERE quantidade >= :qtd`).
- Saldo e movimentação são gravados na mesma transação (tudo ou nada).
- `estoque_minimo` é guardado e exibido; não dispara alerta no MVP.

## Estrutura

```
app/
├── main.py            # criação do app, routers, seed
├── database.py        # engine, sessão, Base
├── models.py          # Categoria, Material, Movimentacao
├── schemas.py         # modelos Pydantic
├── services/estoque.py# regras de negócio
├── routers/           # categorias, materiais, movimentacoes, paginas
├── templates/         # base, estoque, movimentar, cadastro
└── static/            # css e js (o JS só chama a API e renderiza)
tests/                 # cadastro, categorias, entrada, saida, estoque, paginas
```

Camadas: router (HTTP) → service (regra de negócio) → models (dados). Nenhuma regra de negócio fica nos routers nem no JavaScript.

## Fora do escopo do MVP

Autenticação, aprovação de requisições, fornecedores e notas fiscais, relatórios e dashboards, notificações, integrações, multi-filial, edição/exclusão de movimentações, histórico em tela, exportação e indicador de estoque baixo.

Mais detalhes de contexto e decisões do projeto estão em [`claude.md`](claude.md).
