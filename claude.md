# CLAUDE.md — Controle de Materiais de Escritório (MVP)

> Contexto do projeto para o Claude. Leia por inteiro antes de qualquer tarefa.
> Itens `[DEFINIR]` são decisões em aberto: pergunte antes de assumir.

---

## 1. Visão

Aplicação web para **controlar o estoque de materiais de escritório** (papelaria, escrita, informática etc.): cadastrar materiais por categoria, registrar entradas e saídas e consultar o saldo atualizado.

**Problema:** controle informal gera falta de itens, compras duplicadas e falta de visibilidade do saldo.
**Objetivo do MVP:** validar o ciclo cadastrar → entrada → saída → consultar saldo, com regras de negócio confiáveis. Nada além disso, exceto o controle de acesso da Sprint 4.

**Acesso (Sprint 4):** o sistema é usado por **usuários** (nome, CPF único, e-mail) que entram com CPF e senha e têm um de três **perfis**: administrador (mantém usuários), estoquista (cadastra materiais e categorias e informa valores de estoque) e operador (movimenta e pesquisa).

## 2. Stack e arquitetura

| Camada | Escolha | Observação |
|---|---|---|
| Backend | **Python 3.11+ / FastAPI** | API REST + servidor das páginas |
| Validação | Pydantic v2 | schemas de entrada/saída |
| Persistência | SQLite + SQLAlchemy 2.x | decidido: SQLite no MVP |
| Interface web | Jinja2 + HTML semântico, CSS responsivo, JavaScript ES6+ (fetch) | sem framework SPA |
| Autenticação | Sessão em cookie assinado (`SessionMiddleware` + `itsdangerous`); senha com hash `scrypt` da biblioteca padrão | decidido: login por **CPF + senha** |
| Testes | pytest + httpx (TestClient) | |
| Qualidade | ruff (lint + format) | |

Premissas de stack acima podem ser trocadas; confirme antes de mudar.

### Estrutura de pastas

```
.
├── CLAUDE.md
├── README.md
├── requirements.txt
├── docs/                    # guia-de-uso.md, api.md, arquitetura.md
├── app/
│   ├── main.py              # criação do app, middleware, routers, seed, admin inicial
│   ├── config.py            # chave da sessão, duração, variáveis do admin inicial
│   ├── database.py          # engine, sessão, Base
│   ├── models.py            # Categoria, Material, Movimentacao, Usuario
│   ├── schemas.py           # modelos Pydantic
│   ├── seguranca.py         # hash e verificação de senha (scrypt)
│   ├── permissoes.py        # Acao e a matriz PERMISSOES (perfil -> ações)
│   ├── dependencias.py      # usuario_atual, exigir(*acoes)
│   ├── erros.py             # tradução das mensagens de validação (422)
│   ├── services/
│   │   ├── estoque.py       # regras de negócio (entrada, saída, saldo, status, busca)
│   │   └── usuarios.py      # regras de usuários (CPF, perfis, login, último admin)
│   ├── routers/
│   │   ├── autenticacao.py  # /login, /logout, /me
│   │   ├── categorias.py
│   │   ├── materiais.py
│   │   ├── movimentacoes.py
│   │   ├── usuarios.py
│   │   └── paginas.py       # telas HTML, menu por perfil, guarda de páginas
│   ├── templates/           # base, login, acesso_negado, pesquisa, movimentar,
│   │                        # cadastro, usuarios
│   └── static/
│       ├── css/styles.css
│       └── js/              # api, login, sair, pesquisa, movimentar, cadastro, usuarios
└── tests/
    ├── conftest.py          # fixtures: cliente_anonimo, entrar_como, client
    ├── test_cadastro.py, test_categorias.py, test_entrada.py, test_saida.py
    ├── test_estoque.py, test_pesquisa.py, test_fluxo_completo.py, test_erros.py
    ├── test_usuarios.py, test_login.py, test_administrador_inicial.py
    └── test_permissoes.py, test_acesso_rotas.py, test_paginas.py
```

**Camadas:** router (HTTP) → service (regra de negócio) → models (dados). **Regras de negócio ficam em `services/estoque.py` e `services/usuarios.py`**, nunca nos routers nem no JavaScript. **Quem pode o quê fica só em `permissoes.py`**: a API (`exigir`), as páginas e o menu leem a mesma matriz.

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
- **Não registra o usuário** que movimentou (ver seção 12).

**Usuario**
- `id`, `nome` (obrigatório), `cpf` (**único**, só dígitos, com dígitos verificadores válidos), `email` (formato validado; **não** é único)
- `perfil` (`administrador` | `estoquista` | `operador`)
- `senha_hash` (scrypt com sal; a senha nunca é guardada nem devolvida)
- `ativo` (usuário inativo não entra e perde o acesso na hora; nada é apagado)

## 4. Operações do MVP

| Operação | Endpoint | Descrição |
|---|---|---|
| Listar categorias | `GET /categorias` | usado nos formulários e filtros |
| Criar categoria | `POST /categorias` | `nome` obrigatório e único; vazio ou duplicado → `422` |
| Cadastrar material | `POST /materiais` | exige categoria válida |
| Registrar entrada | `POST /materiais/{id}/entrada` | soma ao saldo |
| Registrar saída | `POST /materiais/{id}/saida` | subtrai do saldo, com bloqueio |
| Consultar saldo | `GET /materiais` e `GET /materiais/{id}` | filtros `?categoria_id=`, `?q=` (parte do nome) e `?status=` (`Disponível`/`Indisponível`) |
| Entrar / sair / quem sou | `POST /login`, `POST /logout`, `GET /me` | login por CPF + senha; sessão em cookie |
| Manter usuários | `GET/POST /usuarios`, `GET/PUT /usuarios/{id}`, `POST /usuarios/{id}/inativar` e `/reativar` | CPF único; só o administrador |

Páginas web (todas exigem login, exceto `/login`):

| Página | Rota | Quem acessa |
|---|---|---|
| Pesquisa (estoque agrupado por categoria, com busca e filtros) | `/pesquisa` | estoquista, operador |
| Movimentar | `/movimentar` | operador |
| Cadastro (material e "Nova categoria") | `/materiais/novo` | estoquista |
| Usuários | `/gestao/usuarios` | administrador |
| Login | `/login` | público |

`/` redireciona cada perfil à sua primeira tela. A página de usuários fica em `/gestao/usuarios` porque `/usuarios` é a API.

**Permissões** (matriz em `app/permissoes.py`):

| Ação | Estoquista | Operador | Administrador |
|---|---|---|---|
| Criar categoria | ✅ | | |
| Cadastrar material (estoque inicial e mínimo) | ✅ | | |
| Consultar / pesquisar estoque | ✅ | ✅ | |
| Movimentar (entrada e saída) | | ✅ | |
| Manter usuários | | | ✅ |

Leituras de apoio aceitam "qualquer uma de" várias ações: `GET /categorias` serve a quem consulta, cadastra material ou cria categoria; a lista de materiais serve também a quem movimenta.

Códigos de erro: `401` sem login; `403` perfil sem permissão; `404` material/categoria/usuário inexistente; `422` dado inválido (inclui categoria inválida, quantidade ≤ 0, CPF inválido, filtro de status inválido); `409` saldo insuficiente, CPF de usuário duplicado ou inativar/rebaixar o último administrador. Respostas de erro com mensagem clara em português, sempre como texto em `detail`.

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
- **CA-06 Agrupamento por categoria:** a tela de estoque (hoje a tela **Pesquisa**) permite filtrar e listar todos os materiais e seus saldos **agrupados por categoria**.

### Usuários e acesso
- **CA-07 CPF único:** não é permitido duplicar usuários; o campo único é o **CPF**. CPF repetido (mesmo com máscara diferente, mesmo de usuário inativo) → rejeitar com `409` e não gravar nada. O CPF precisa ter dígitos verificadores válidos.
- **CA-08 Permissões por perfil:** cada perfil só faz o que a matriz da seção 4 permite, **na API e nas telas**. Sem login → `401` (páginas: redireciona ao login); sem permissão → `403`. Estoquista cadastra e informa valores de estoque; operador só movimenta e pesquisa; administrador só mantém usuários.

## 6. Regras de negócio e integridade

1. Quantidade de entrada/saída: inteiro **maior que zero**.
2. Saldo **nunca negativo**.
3. Estoque inicial no cadastro: inteiro ≥ 0 (padrão 0). Material cadastrado com 0 nasce "Indisponível".
4. Atualização de saldo + gravação da movimentação ocorrem **na mesma transação** (tudo ou nada).
5. A verificação de saldo suficiente e a subtração devem ser **atômicas** (evitar saída dupla concorrente), por exemplo `UPDATE ... WHERE quantidade >= :qtd`.
6. Status é calculado a partir do saldo; não existe campo editável de status.
7. `estoque_minimo` é guardado e exibido; **não dispara alerta no MVP** (decidido: indicador de "estoque baixo" fora do MVP).
8. CPF é guardado só com dígitos e validado pelos dígitos verificadores; é único. E-mail tem formato validado e não é único.
9. Senha: mínimo de **6** caracteres (protótipo), guardada com hash `scrypt` e sal; nunca devolvida pela API. **Senha padrão `123456`**: vale para usuário cadastrado sem senha informada e para o administrador padrão.
10. O login responde igual para CPF inexistente, senha errada e usuário inativo ("CPF ou senha inválidos."), e o hash é calculado sempre, para não revelar quais CPFs existem.
11. A sessão (cookie assinado, `HttpOnly`, `SameSite=Lax`, 8 h) **relê o usuário no banco a cada requisição**: inativar um usuário ou mudar o perfil dele vale na próxima chamada.
12. Usuários não são apagados, apenas inativados. O **último administrador ativo** não pode ser inativado nem rebaixado.
13. O CPF de um usuário não pode ser alterado depois de cadastrado.

## 7. Plano em sprints (1 a 3 concluídas; 4 descrita ao final)

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

### Sprint 4 — Usuários, login e permissões (pedido explícito, amplia o escopo original)
1. Modelo `Usuario`, CPF único com validação, hash de senha e CRUD da API (inativar em vez de excluir)
2. Login por CPF + senha, sessão em cookie, `/me` e `/logout` (nova dependência: `itsdangerous`)
3. Matriz de permissões, `exigir(*acoes)` nas rotas da API e administrador inicial por variáveis de ambiente
4. Telas: login, sair, usuários e **Pesquisa** (substitui a tela Estoque); menu e páginas por perfil
5. Documentação (README, `docs/`) e este arquivo
- Testes: CA-07, CA-08, login/sessão, acesso por perfil e rota (`test_acesso_rotas.py`), páginas por perfil e busca
- **Pronto quando:** CA-01 a CA-08 passam e cada perfil, no navegador, enxerga e faz somente o que a matriz permite.

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
- Testes de **regra de negócio** usam o fixture `client` (logado com todas as permissões, para não depender da matriz); testes de **acesso** usam `cliente_anonimo` + `entrar_como(perfil)` com a **matriz real**

## 9. Fora do escopo (não implementar sem pedido explícito)

Aprovação de requisições, fornecedores e notas fiscais, relatórios e dashboards, notificações, integrações (ERP/e-mail), multi-filial, edição/exclusão de movimentações, histórico em tela, app mobile nativo, exportação.

Dentro de usuários e acesso, também fora do escopo por ora: recuperação/troca de senha pelo próprio usuário, limite de tentativas de login, login por provedor externo (SSO), edição de CPF e exclusão definitiva de usuários, e registrar quem fez cada movimentação.

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

O banco é o arquivo `estoque.db`, criado na raiz ao iniciar o app, junto com o seed das categorias. As tabelas novas são criadas sozinhas, mas **não há migração**: colunas novas em tabelas já existentes exigem recriar o banco ou alterar a tabela à mão.

### Variáveis de ambiente

| Variável | Para quê |
|---|---|
| `ESTOQUE_ADMIN_CPF` e `ESTOQUE_ADMIN_SENHA` | definem o **primeiro administrador**, criado ao iniciar **só se não existir nenhum usuário** (CPF válido, senha com 6+ caracteres). **Sem elas, vale o administrador padrão do protótipo: CPF `529.982.247-25`, senha `123456`** (o log avisa que a senha é a padrão) |
| `ESTOQUE_ADMIN_NOME`, `ESTOQUE_ADMIN_EMAIL` | opcionais (padrões: `Administrador`, `administrador@estoque.local`) |
| `ESTOQUE_SECRET_KEY` | chave que assina o cookie de sessão. Defina um valor fixo e longo; sem ela uma chave aleatória é gerada a cada início e as sessões não sobrevivem a reinícios |

Para trocar o administrador padrão (PowerShell):

```powershell
$env:ESTOQUE_ADMIN_CPF = "SEU-CPF"; $env:ESTOQUE_ADMIN_SENHA = "uma-senha-forte"; $env:ESTOQUE_SECRET_KEY = "um-valor-longo-e-fixo"
uvicorn app.main:app --reload
```

> **Protótipo:** por decisão do dono do projeto, a segurança de senhas foi simplificada (mínimo de 6 caracteres, senha padrão `123456`, administrador padrão no código). Isso não serve para uso real; ver seção 12.

O cookie de sessão não tem a flag `Secure` (funciona em `http://localhost`). Ao publicar em HTTPS, ligue `https_only` no `SessionMiddleware`.

## 12. Decisões em aberto

- [x] Manter SQLite no MVP ou usar outro banco? → **SQLite**
- [x] Exibir indicador de "estoque baixo" usando `estoque_minimo`? → **Não, fora do MVP**
- [x] Categorias poderão ser criadas pela interface ou só via seed? → **Pela interface** (só criar; editar/excluir fora do escopo), além do seed
- [x] Haverá login em versão futura (impacta registrar "quem retirou")? → ~~Ignorar no MVP~~ **Superado na Sprint 4**: login por CPF + senha
- [x] Como o usuário se identifica? → **CPF + senha**
- [x] O estoquista também movimenta e pesquisa? → **Não**: só o descrito (cadastros, valores de estoque e consulta, ver matriz na seção 4)
- [x] Quem mantém os usuários? → **Novo perfil Administrador** (fora das duas permissões originais)
- [x] Como remover um usuário? → **Inativar**
- [x] Segurança das senhas no protótipo? → **Simplificada**: senhas de 6+ caracteres, senha padrão `123456` e administrador padrão (CPF `529.982.247-25`). **Rever antes de uso real** (tamanho mínimo, senha padrão, administrador no código, chave de sessão)
- [ ] Registrar **quem** fez cada entrada e saída (`usuario_id` em `Movimentacao`)? Foi sugerido na Sprint 4, **não foi implementado**; exige migração do banco
- [ ] "Informar valores de estoque" inclui **editar** estoque inicial/mínimo de um material já cadastrado? Hoje só é possível ao cadastrar; não há endpoint de edição
- [ ] Limite de tentativas de login e troca de senha pelo próprio usuário?

## 13. Glossário

- **Saldo / quantidade:** quantidade atual de um material em estoque
- **Entrada:** aumento de saldo (compra, reposição)
- **Saída:** retirada de material, reduz o saldo
- **Estoque mínimo:** nível de referência para reposição
- **Indisponível:** status de material com saldo 0
- **Perfil:** papel do usuário (administrador, estoquista ou operador); define o que ele pode fazer
- **Administrador:** perfil que mantém os usuários
- **Estoquista:** perfil que cadastra materiais e categorias, informa valores de estoque e consulta
- **Operador:** perfil que movimenta materiais e pesquisa o estoque
- **Matriz de permissões:** tabela em `app/permissoes.py` que liga cada perfil às ações permitidas