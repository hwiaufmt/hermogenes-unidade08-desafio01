# CLAUDE.md — Controle de Materiais de Escritório (MVP)

> Contexto do projeto para o Claude. Leia por inteiro antes de qualquer tarefa.
> Itens `[DEFINIR]` são decisões em aberto: pergunte antes de assumir.

---

## 1. Visão

Aplicação web para **controlar o estoque de materiais de escritório** (papelaria, escrita, informática etc.): cadastrar materiais por categoria, registrar entradas e saídas e consultar o saldo atualizado.

**Problema:** controle informal gera falta de itens, compras duplicadas e falta de visibilidade do saldo.
**Objetivo do MVP:** validar o ciclo cadastrar → entrada → saída → consultar saldo, com regras de negócio confiáveis. Nada além disso.

## 2. Stack e arquitetura

| Camada | Escolha | Observação |
|---|---|---|
| Backend | **Python 3.11+ / FastAPI** | API REST + servidor das páginas |
| Validação | Pydantic v2 | schemas de entrada/saída |
| Persistência | SQLite + SQLAlchemy 2.x | decidido: SQLite no MVP |
| Interface web | Jinja2 + HTML semântico, CSS responsivo, JavaScript ES6+ (fetch) | sem framework SPA |
| Testes | pytest + httpx (TestClient) | |
| Qualidade | ruff (lint + format) | |

Premissas de stack acima podem ser trocadas; confirme antes de mudar.

### Estrutura de pastas

```
.
├── CLAUDE.md
├── README.md
├── requirements.txt
├── app/
│   ├── main.py              # criação do app, routers, seed
│   ├── database.py          # engine, sessão, Base
│   ├── models.py            # Categoria, Material, Movimentacao
│   ├── schemas.py           # modelos Pydantic
│   ├── services/
│   │   └── estoque.py       # regras de negócio (entrada, saída, saldo, status)
│   ├── routers/
│   │   ├── categorias.py
│   │   ├── materiais.py
│   │   ├── movimentacoes.py
│   │   └── paginas.py       # rotas que renderizam HTML
│   ├── templates/           # base.html, estoque.html, cadastro.html, movimentar.html
│   └── static/
│       ├── css/styles.css
│       └── js/              # estoque.js, cadastro.js, movimentar.js
└── tests/
    ├── test_cadastro.py
    ├── test_entrada.py
    ├── test_saida.py
    └── test_estoque.py
```

**Camadas:** router (HTTP) → service (regra de negócio) → models (dados). **Regras de negócio ficam em `services/estoque.py`**, nunca nos routers nem no JavaScript.

## 3. Modelo de dados

**Categoria**
- `id`, `nome` (único, obrigatório)
- Seed inicial: **Papelaria**, **Escrita**, **Informática**

**Material**
- `id`
- `nome` (obrigatório)
- `categoria_id` (FK obrigatória para Categoria)
- `quantidade` (inteiro ≥ 0; é o **saldo atual**)
- `estoque_minimo` (inteiro ≥ 0)
- `status` — **derivado, não armazenado**: `"Indisponível"` se `quantidade == 0`, caso contrário `"Disponível"`

**Movimentacao** (registro simples para rastreabilidade; sem tela de histórico no MVP)
- `id`, `material_id`, `tipo` (`entrada` | `saida`), `quantidade` (inteiro > 0), `saldo_apos`, `data` (UTC)

## 4. Operações do MVP

| Operação | Endpoint | Descrição |
|---|---|---|
| Listar categorias | `GET /categorias` | usado nos formulários e filtros |
| Criar categoria | `POST /categorias` | `nome` obrigatório e único; vazio ou duplicado → `422` |
| Cadastrar material | `POST /materiais` | exige categoria válida |
| Registrar entrada | `POST /materiais/{id}/entrada` | soma ao saldo |
| Registrar saída | `POST /materiais/{id}/saida` | subtrai do saldo, com bloqueio |
| Consultar saldo | `GET /materiais` e `GET /materiais/{id}` | filtro `?categoria_id=` |

Páginas web: **Estoque** (`/`), **Cadastro** (`/materiais/novo`, inclui formulário "Nova categoria"), **Movimentar** (`/movimentar`).

Códigos de erro: `404` material/categoria inexistente; `422` dado inválido (inclui categoria inválida e quantidade ≤ 0); `409` saldo insuficiente. Respostas de erro com mensagem clara em português.

## 5. Critérios de aceite

### Entrada de materiais
- **CA-01 Cadastro por categoria:** o sistema só salva um novo material se ele estiver associado a uma categoria válida (ex.: Papelaria, Escrita, Informática). Categoria ausente ou inexistente → rejeitar e não gravar nada.
- **CA-02 Cálculo do novo saldo:** ao registrar uma entrada, o sistema soma a quantidade ao saldo anterior.
  `Saldo Atual = Saldo Anterior + Quantidade de Entrada`

### Saída de materiais
- **CA-03 Bloqueio por saldo insuficiente:** o sistema impede a saída se a quantidade solicitada for maior que o saldo disponível. O saldo permanece inalterado e nenhuma movimentação é gravada.
- **CA-04 Atualização pós-retirada:** ao confirmar a saída, o saldo é deduzido imediatamente.
  `Saldo Atual = Saldo Anterior - Quantidade de Saída`

### Controle e alertas
- **CA-05 Sinalização de zerado:** quando o saldo chegar a 0, o status muda automaticamente para **"Indisponível"** (sem ação manual). Uma nova entrada devolve o status para "Disponível".
- **CA-06 Agrupamento por categoria:** a tela de estoque permite filtrar e listar todos os materiais e seus saldos **agrupados por categoria**.

## 6. Regras de negócio e integridade

1. Quantidade de entrada/saída: inteiro **maior que zero**.
2. Saldo **nunca negativo**.
3. Estoque inicial no cadastro: inteiro ≥ 0 (padrão 0). Material cadastrado com 0 nasce "Indisponível".
4. Atualização de saldo + gravação da movimentação ocorrem **na mesma transação** (tudo ou nada).
5. A verificação de saldo suficiente e a subtração devem ser **atômicas** (evitar saída dupla concorrente), por exemplo `UPDATE ... WHERE quantidade >= :qtd`.
6. Status é calculado a partir do saldo; não existe campo editável de status.
7. `estoque_minimo` é guardado e exibido; **não dispara alerta no MVP** (decidido: indicador de "estoque baixo" fora do MVP).

## 7. Plano em 3 sprints

### Sprint 1 — Fundação e cadastro
- Setup do projeto (FastAPI, SQLAlchemy, pytest, ruff, estrutura de pastas)
- Modelos `Categoria` e `Material`, seed das categorias
- `GET /categorias`, `POST /categorias`, `POST /materiais`, `GET /materiais`
- Tela de cadastro (com formulário "Nova categoria") e listagem básica
- Testes: CA-01 e criação de categoria (nova, duplicada, vazia)
- **Pronto quando:** é possível cadastrar material com categoria válida e ver na lista; categoria inválida é rejeitada.

### Sprint 2 — Entrada e saída
- Modelo `Movimentacao`
- Service de estoque: `registrar_entrada`, `registrar_saida`, `calcular_status`
- Endpoints de entrada e saída; tela **Movimentar**
- Mensagens de erro de saldo insuficiente
- Testes: CA-02, CA-03, CA-04, CA-05
- **Pronto quando:** entradas somam, saídas subtraem, saída acima do saldo é bloqueada e saldo 0 mostra "Indisponível".

### Sprint 3 — Consulta, agrupamento e acabamento
- Tela de **Estoque** agrupada por categoria, com filtro (CA-06)
- Destaque visual de "Indisponível"
- Responsividade e acessibilidade
- Testes de ponta a ponta do fluxo completo
- README (como rodar, testar) e revisão final dos critérios de aceite
- **Pronto quando:** todos os CA-01 a CA-06 passam e o fluxo completo funciona em desktop e celular.

## 8. Padrões de código

### Python
- Type hints em todas as funções públicas
- Funções **pequenas**, uma responsabilidade
- Nomes de domínio em português (`registrar_saida`, `calcular_status`); termos técnicos consagrados em inglês
- Exceções de domínio no service (ex.: `SaldoInsuficienteError`) convertidas em HTTP no router
- Sem lógica de negócio em routers; sem SQL solto fora da camada de dados
- ruff sem avisos

### Interface web
- HTML semântico; todo input com `label`; foco visível
- CSS mobile-first, variáveis em `:root`
- JavaScript ES6+ legível, sem variáveis globais, funções pequenas
- O JavaScript só chama a API e renderiza; **não recalcula saldo nem status**
- Exibir mensagens de erro da API ao usuário de forma clara

### Testes
- Cada critério de aceite tem ao menos um teste nomeado com o ID (ex.: `test_ca03_saida_bloqueada_por_saldo_insuficiente`)
- Banco de testes isolado (SQLite em memória)

## 9. Fora do escopo (não implementar sem pedido explícito)

Autenticação/perfis, aprovação de requisições, fornecedores e notas fiscais, relatórios e dashboards, notificações, integrações (ERP/e-mail), multi-filial, edição/exclusão de movimentações, histórico em tela, app mobile nativo, exportação.

## 10. Forma de trabalho (como o Claude deve agir)

1. **Alinhar antes de criar:** em cada tarefa nova, confirme o entendimento e liste dúvidas/suposições antes de gerar código.
2. **Um passo por vez:** entregue por sprint e, dentro dela, em partes pequenas e revisáveis.
3. **Respeitar o escopo:** nada fora das seções 4 e 5.
4. **Perguntar nos `[DEFINIR]`:** não decidir sozinho.
5. **Explicar o que mudou** ao alterar arquivos.
6. **Não refatorar sem pedido.**
7. Ao concluir uma sprint, verificar cada critério de aceite listado nela.

## 11. Como rodar

Requer Python 3.11+. Na primeira vez, crie o ambiente e instale as dependências.

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
uvicorn app.main:app --reload   # app em http://localhost:8000 (docs em /docs)
pytest                          # testes (SQLite em memória)
ruff check . && ruff format .   # lint e formatação
```

O banco é o arquivo `estoque.db`, criado na raiz ao iniciar o app, junto com o seed das categorias.

## 12. Decisões em aberto

- [x] Manter SQLite no MVP ou usar outro banco? → **SQLite**
- [x] Exibir indicador de "estoque baixo" usando `estoque_minimo`? → **Não, fora do MVP**
- [x] Categorias poderão ser criadas pela interface ou só via seed? → **Pela interface** (só criar; editar/excluir fora do escopo), além do seed
- [x] Haverá login em versão futura (impacta registrar "quem retirou")? → **Ignorar no MVP**

## 13. Glossário

- **Saldo / quantidade:** quantidade atual de um material em estoque
- **Entrada:** aumento de saldo (compra, reposição)
- **Saída:** retirada de material, reduz o saldo
- **Estoque mínimo:** nível de referência para reposição
- **Indisponível:** status de material com saldo 0