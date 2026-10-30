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
├── docs/                    # visao-do-produto.md, guia-de-uso.md, api.md, arquitetura.md
├── app/
│   ├── main.py              # criação do app, middleware, routers, seed, admin inicial
│   ├── config.py            # chave da sessão, duração, variáveis do admin inicial
│   ├── database.py          # engine, sessão, Base
│   ├── models.py            # Categoria, Material, Movimentacao, Usuario
│   ├── migracoes.py         # migração leve: só acrescenta colunas que faltam, ao iniciar
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
│   │   ├── saldos.py        # GET /saldos
│   │   ├── usuarios.py
│   │   └── paginas.py       # telas HTML, menu por perfil, guarda de páginas
│   ├── templates/           # base, login, acesso_negado, pesquisa, saldos,
│   │                        # movimentar, cadastro, usuarios
│   └── static/
│       ├── css/styles.css
│       └── js/              # api, tabelas, login, sair, pesquisa, saldos, movimentar,
│                            # cadastro, usuarios
└── tests/
    ├── conftest.py          # fixtures: cliente_anonimo, entrar_como, client
    ├── test_cadastro.py, test_categorias.py, test_entrada.py, test_saida.py
    ├── test_edicao_categoria.py, test_categoria_nome_sem_case.py
    ├── test_exclusao_material.py, test_migracoes.py
    ├── test_estoque.py, test_pesquisa.py, test_saldos.py, test_fluxo_completo.py, test_erros.py
    ├── test_usuarios.py, test_login.py, test_administrador_inicial.py
    └── test_permissoes.py, test_acesso_rotas.py, test_paginas.py
```

**Camadas:** router (HTTP) → service (regra de negócio) → models (dados). **Regras de negócio ficam em `services/estoque.py` e `services/usuarios.py`**, nunca nos routers nem no JavaScript. **Quem pode o quê fica só em `permissoes.py`**: a API (`exigir`), as páginas e o menu leem a mesma matriz.

## 3. Modelo de dados

**Categoria**
- `id`, `nome` (obrigatório; único **sem diferenciar maiúsculas de minúsculas**, e **editável** pelo estoquista)
- Seed inicial: **Papelaria**, **Escrita**, **Informática**

**Material**
- `id`
- `nome` (obrigatório)
- `categoria_id` (FK obrigatória para Categoria)
- `quantidade` (inteiro ≥ 0; é o **saldo atual**)
- `estoque_minimo` (inteiro ≥ 0)
- `excluido_em` — data e hora (UTC) da **exclusão lógica**; vazia = material ativo. Material excluído continua na tabela, mas some das telas e das consultas
- `status` — **derivado, não armazenado**: `"Indisponível"` se `quantidade == 0`, caso contrário `"Disponível"`. Nas telas aparece como **Sim/Não** ("Disponível?"); a API continua devolvendo o texto

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
| Listar categorias | `GET /categorias` | usado nos formulários e filtros; informa `total_materiais` de cada categoria |
| Criar categoria | `POST /categorias` | `nome` obrigatório e único **sem diferenciar maiúsculas de minúsculas** ("Escrita" = "escrita"); vazio ou duplicado → `422` |
| Editar categoria | `PUT /categorias/{id}` | corpo `{nome, confirmar}`; mesmas regras de nome; com materiais **exige `confirmar: true`**, senão `409` com `afetados` (quantos registros seriam afetados) e nada é gravado |
| Cadastrar material | `POST /materiais` | exige categoria válida |
| Excluir material | `DELETE /materiais/{id}` | **exclusão lógica**; com saldo > 0 exige `?confirmar=true`, senão `409` com `saldo` e nada é gravado; sem saldo exclui direto; excluído → `404` em consulta e movimentação |
| Registrar entrada | `POST /materiais/{id}/entrada` | soma ao saldo |
| Registrar saída | `POST /materiais/{id}/saida` | subtrai do saldo, com bloqueio |
| Consultar saldo | `GET /materiais` e `GET /materiais/{id}` | filtros `?categoria_id=`, `?q=` (parte do nome) e `?status=` (`Disponível`/`Indisponível`); não trazem materiais excluídos |
| Consultar saldos | `GET /saldos` | por categoria: `total_materiais`, `total_unidades` e `total_indisponiveis`, com o saldo e o status de cada material (sem os excluídos); `totais` traz o total geral. Categorias sem materiais aparecem com zeros. Categorias e materiais em ordem alfabética sem diferenciar maiúsculas |
| Entrar / sair / quem sou | `POST /login`, `POST /logout`, `GET /me` | login por CPF + senha; sessão em cookie |
| Manter usuários | `GET/POST /usuarios`, `GET/PUT /usuarios/{id}`, `POST /usuarios/{id}/inativar` e `/reativar` | CPF único; só o administrador |

Páginas web (todas exigem login, exceto `/login`):

| Página | Rota | Quem acessa |
|---|---|---|
| Pesquisa (estoque agrupado por categoria, com busca e filtros; botão **Excluir** só para quem pode excluir) | `/pesquisa` | estoquista, operador |
| Saldos (total geral e tabela de materiais: Material, Quantidade, Categoria e Disponível, agrupada por categoria em ordem alfabética) | `/estoque/saldos` | estoquista, operador |
| Movimentar | `/movimentar` | operador |
| Cadastro (material, "Nova categoria" e lista de categorias com edição e confirmação) | `/materiais/novo` | estoquista |
| Usuários | `/gestao/usuarios` | administrador |
| Login | `/login` | público |

`/` redireciona cada perfil à sua primeira tela. A página de usuários fica em `/gestao/usuarios` e a de saldos em `/estoque/saldos` porque `/usuarios` e `/saldos` são a API (a primeira rota registrada responderia JSON ao navegador).

**Permissões** (matriz em `app/permissoes.py`):

| Ação | Estoquista | Operador | Administrador |
|---|---|---|---|
| Criar categoria | ✅ | | |
| Editar categoria (com aviso de impacto) | ✅ | | |
| Cadastrar material (estoque inicial e mínimo) | ✅ | | |
| Excluir material (exclusão lógica, com confirmação se houver saldo) | ✅ | | |
| Consultar / pesquisar estoque e saldos | ✅ | ✅ | |
| Movimentar (entrada e saída) | | ✅ | |
| Manter usuários | | | ✅ |

Leituras de apoio aceitam "qualquer uma de" várias ações: `GET /categorias` serve a quem consulta, cadastra material, cria ou edita categoria; a lista de materiais serve também a quem movimenta.

Códigos de erro: `401` sem login; `403` perfil sem permissão; `404` material/categoria/usuário inexistente; `422` dado inválido (inclui categoria inválida, quantidade ≤ 0, CPF inválido, filtro de status inválido); `409` saldo insuficiente, CPF de usuário duplicado, inativar/rebaixar o último administrador, alterar categoria com materiais sem confirmação (a resposta traz também `afetados`, um inteiro), ou excluir material com saldo sem confirmação (a resposta traz também `saldo`, um inteiro). Respostas de erro com mensagem clara em português, sempre como texto em `detail`.

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

### Categorias e consulta de saldo (CA-09 e CA-10: Sprint 5; CA-11: Sprint 6, redefinido pelo CA-13 na tela; concluídos)
- **CA-09 Edição de categoria:** o estoquista pode alterar o nome de uma categoria. Nome vazio ou já usado por outra categoria (**sem diferenciar maiúsculas de minúsculas**) → `422`, sem gravar; categoria inexistente → `404`; outros perfis → `403`.
- **CA-10 Aviso de impacto:** antes de alterar uma categoria que tem materiais, o sistema informa **quantos registros serão afetados** e só grava com confirmação. Sem confirmação (`confirmar: true`), o servidor responde `409` com a quantidade (`afetados`) e **nada é gravado**. Categoria sem materiais grava direto. Nome repetido é recusado antes de pedir a confirmação.
- **CA-11 Consulta de saldo** (a API segue assim; **na tela, o CA-13 redefine** a apresentação): a visão **Saldos** mostra, por categoria, o total de materiais, o total de unidades e quantos estão indisponíveis, e o saldo atual de cada material, sempre coerente com as entradas e saídas já registradas. Mostra também o **total geral** e inclui as categorias sem materiais (com zeros).

### Exclusão de materiais e consulta por material (Sprint 8, concluída)
- **CA-12 Exclusão lógica de material:** o estoquista pode excluir um material. O registro **não é apagado do banco**: fica marcado como excluído e **deixa de aparecer** em todas as telas e consultas (Pesquisa, Saldos, Movimentar e nos totais) e de aceitar movimentações; consultar ou movimentar um material excluído → `404`. Material com **saldo maior que zero** só é excluído com confirmação (`confirmar: true`): sem ela, o servidor responde `409` informando o saldo e **nada é gravado**; com saldo 0, exclui direto. As movimentações antigas **continuam guardadas**. Outros perfis → `403`.
- **CA-13 Consulta por material:** a tela Saldos lista os materiais com as colunas **Material, Quantidade, Categoria e Disponível**, **agrupados por categoria em ordem alfabética** (e por nome dentro da categoria), sem materiais excluídos e sempre coerente com as entradas e saídas. Isso **redefine** o CA-11 na tela (os totais por categoria deixam de ser exibidos; o total geral continua).
- **CA-14 Disponibilidade em sim ou não:** nas telas (Pesquisa, Saldos e filtros), a disponibilidade aparece como **Sim** (saldo maior que zero) ou **Não** (saldo 0). A regra do status (CA-05) e o campo `status` da API não mudam.

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
14. O nome da categoria é único **sem diferenciar maiúsculas de minúsculas** ("Escrita" é igual a "escrita"), na criação, na edição e no seed. A comparação é feita no service com `casefold` (o `lower()` do SQLite só trata ASCII); **acentos diferenciam** ("Informatica" ≠ "Informática"). Na mensagem de erro aparece o nome já existente. O índice único do banco continua diferenciando maiúsculas (mudá-lo exigiria uma migração maior que a leve da regra 18) e serve só de rede de segurança.
15. Alterar o nome de uma categoria que tem materiais exige confirmação explícita do cliente (`confirmar: true`); sem ela o servidor informa quantos registros seriam afetados e não grava. A regra vale só para a edição de categoria.
16. Na consulta de saldos, **todos os totais** (por categoria e geral) são calculados no service, nunca no JavaScript. A contagem de indisponíveis reusa `calcular_status`. Categorias e materiais saem em ordem alfabética sem diferenciar maiúsculas de minúsculas.
17. A exclusão de material é **lógica**: o registro continua no banco com `excluido_em` preenchido, e as suas movimentações **não são apagadas**. **Todo ponto que lê materiais ignora os excluídos** (listagem e busca, consulta por id, saldos, totais da categoria, aviso de "registros afetados" e movimentação). Material com saldo maior que zero só é excluído com `confirmar`; a tela busca o saldo atual antes de pedir a confirmação. Não há como restaurar pela interface.
18. **Migração leve:** ao iniciar, `app/migracoes.py` confere e acrescenta as colunas novas que faltam (hoje `materiais.excluido_em`), com `ALTER TABLE ... ADD COLUMN`. Só **adiciona** colunas vazias, nunca altera nem apaga dados, e é idempotente. **Outras mudanças de estrutura** (alterar ou remover colunas, mudar índices) continuam exigindo recriar o banco ou alterar a tabela à mão. Com `--reload`, o servidor aplica a migração assim que o código novo é salvo.
19. Nas telas, a disponibilidade é rotulada **Sim/Não**; a tradução do texto da API (`"Disponível"` → Sim; demais → Não) é só um rótulo, feito em um único lugar do JavaScript (`rotuloDisponivel`). O JavaScript não calcula o status.

## 7. Plano em sprints (1 a 8 concluídas; 9 planejada)

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

### Sprint 5 — Edição de categoria com aviso de impacto (concluída; pedido explícito, amplia o escopo)
Hoje a categoria só pode ser criada. Passa a poder ser editada, e **antes de gravar o sistema informa quantos registros serão afetados**.
1. **Service e API:** nova ação `EDITAR_CATEGORIA` na matriz (concedida ao **estoquista**); `PUT /categorias/{id}` altera o **nome** (único sem diferenciar maiúsculas; vazio ou repetido → `422`; categoria inexistente → `404`). Se a categoria tem materiais, o servidor **exige confirmação**: sem ela responde `409` informando a quantidade de materiais afetados; com a confirmação, grava. Sem materiais, grava direto. A lista de categorias passa a informar quantos materiais cada uma tem.
2. **Tela:** na página Cadastro, lista de categorias com botão "Editar" e janela de confirmação acessível (`<dialog>`) que mostra "esta mudança afetará N registros" antes de gravar.
3. **Fechamento:** testes CA-09 e CA-10, documentação (README, `docs/`) e este arquivo.
- Regra do aviso vale **só para a edição de categoria** (decidido); não muda o banco (o material liga à categoria pelo id), logo não há migração.
- Durante a sprint o dono do projeto pediu que o nome da categoria **não diferencie maiúsculas de minúsculas** ("Escrita" = "escrita"), na criação, na edição e no seed (regra 14).
- **Pronto quando:** renomear uma categoria sem materiais grava direto; com materiais, só grava depois de informar a quantidade afetada e receber a confirmação; o estoquista consegue pela tela e os demais perfis recebem `403`. **Verificado:** CA-09 e CA-10 passam (testes `test_ca09_*` e `test_ca10_*`) e a tela foi conferida no navegador em desktop e celular.

### Sprint 6 — Consulta de saldo de materiais (concluída)
Uma visão de leitura para **consultar saldos**: resumo por categoria e saldo por material (decidido). Usa só dados que já existem; sem migração.
1. **Service e API:** `GET /saldos` devolve, por categoria, o total de materiais, o total de unidades e quantos estão indisponíveis, com o saldo e o status de cada material, mais o **total geral** (`totais`). Os totais são calculados no service, nunca no JavaScript. Categorias sem materiais aparecem com zeros. Permissão: `CONSULTAR_ESTOQUE`.
2. **Tela:** página **Saldos** em `/estoque/saldos` (item no menu de quem consulta), com o total geral, o resumo por categoria e, abaixo, os saldos por material; "Indisponível" destacado como na Pesquisa; botão "Atualizar saldos".
3. **Fechamento:** testes CA-11, documentação e este arquivo.
- Fora desta sprint: saldo em data passada e extrato de movimentações (histórico em tela segue fora do escopo).
- **Pronto quando:** a tela mostra os totais corretos por categoria e o saldo de cada material, acompanhando entradas e saídas, para estoquista e operador. **Verificado:** CA-11 passa (testes `test_ca11_*`) e a tela foi conferida no navegador em desktop e celular, com os números acompanhando uma saída.

### Sprint 7 — Documento de visão do produto (concluída)
Documento de produto, não de código: `docs/visao-do-produto.md` (Markdown, decidido).
1. **Alinhar o sumário** (**feito**, com o dono do projeto). Decisões: público = **equipe e donos do produto** (tom de produto, com detalhe de perfis, escopo, evolução e riscos); contexto = **genérico, um escritório** (sem organização, equipe nem números inventados; onde faltar dado, "a definir"); métricas = **propostas por mim, marcadas como hipóteses** (sem metas numéricas inventadas); **sem seção de "Próximos passos"** (o documento descreve o que existe hoje).
   Sumário final: (1) Resumo; (2) Problema e oportunidade; (3) Usuários e perfis; (4) Objetivos e proposta de valor; (5) Escopo atual; (6) Fora do escopo; (7) Evolução do produto (as sprints em linguagem de produto); (8) Princípios do produto; (9) Métricas de sucesso (hipóteses); (10) Premissas, restrições e riscos (inclusive as simplificações de segurança do protótipo, como limitações do estado atual).
2. **Escrever o documento** nesse sumário, em português, claro e direto (cerca de 4 a 6 páginas), separando o que o sistema **faz** do que **não faz**.
3. **Revisar contra o sistema** (toda afirmação deve valer hoje), ligar o documento no README e em `docs/`. **Feito.** A revisão achou e corrigiu cinco imprecisões: (a) "todas as mensagens em português" era falso, pois endereços inexistentes (`404 "Not Found"`) e métodos não permitidos (`405 "Method Not Allowed"`) respondem em inglês (corrigido também no README e em `docs/api.md`); (b) uma linha "quem decide compras" sugeria um perfil que não existe; (c) "histórico dessa pessoa" sugeria um histórico que o sistema não tem; (d) o princípio "avisar antes de afetar" soava geral, mas hoje vale só para a edição de categoria; (e) a tela Saldos poderia ser confundida com os relatórios e painéis que estão fora do escopo.
- **Pronto quando:** o documento está escrito, revisado e versionado, e nada nele contradiz o que o sistema faz. **Verificado** contra o código e o comportamento real (sessão de 8 h, categorias iniciais, permissões, respostas de erro) e ligado no README e em `docs/`.

### Sprint 8 — Exclusão lógica de materiais e consulta por material (concluída; pedido explícito, amplia o escopo)
Três mudanças pedidas pelo dono do projeto: (1) excluir materiais de forma **lógica**; (2) a tela de saldos passa a listar **cada material** (nome, quantidade, categoria e disponibilidade), agrupado por categoria em ordem alfabética; (3) a disponibilidade passa a ser exibida como **Sim** ou **Não**.
1. **Exclusão lógica (service e API).** Nova coluna `excluido_em` em `materiais` (data e hora UTC; vazia = material ativo), criada por uma **migração leve e idempotente ao iniciar** (`ALTER TABLE ... ADD COLUMN`, sem tocar nos dados). É a **primeira mudança em uma tabela existente**: o `estoque.db` já em uso se atualiza sozinho (recomenda-se copiar o arquivo antes). Nova ação `EXCLUIR_MATERIAL`, concedida ao **estoquista**; `DELETE /materiais/{id}` faz a exclusão lógica. **Material com saldo maior que zero exige confirmação** (`confirmar: true`): sem ela o servidor responde `409` informando o saldo e nada é gravado; com saldo 0, exclui direto. O material excluído **some** de Pesquisa, Saldos, Movimentar e dos totais (inclusive o total de materiais por categoria e o aviso de "registros afetados" da edição de categoria); consultá-lo ou movimentá-lo dá `404`. As **movimentações antigas continuam guardadas**.
2. **Telas.** Botão **Excluir** na Pesquisa, só para quem tem a permissão, com janela de confirmação (`<dialog>`) que mostra o saldo quando houver. Tela **Saldos**: os cartões do total geral continuam; a tabela única **substitui** "Resumo por categoria" e "Saldo por material" e tem as colunas **Material | Quantidade | Categoria | Disponível**, **agrupada por categoria em ordem alfabética** e com os materiais em ordem alfabética dentro de cada categoria, sem coluna extra à esquerda. **Disponível** aparece como **Sim** ou **Não** em Pesquisa, Saldos e nos filtros ("Disponível: Todos, Sim, Não"). A **API não muda** (`status` continua `"Disponível"`/`"Indisponível"`, e `GET /saldos` continua devolvendo os totais por categoria; a tela é que não os exibe mais).
3. **Fechamento:** testes CA-12 a CA-14, documentação (README, `docs/`, visão do produto) e este arquivo.
- Fora desta sprint: **restaurar** um material excluído (a exclusão fica só no banco) e excluir categorias.
- **Pronto quando:** o estoquista exclui um material pela tela (com confirmação quando há saldo) e ele deixa de aparecer em todo o sistema, sem apagar o histórico; o banco já existente é atualizado sem perda de dados; a tela Saldos mostra a tabela nas colunas pedidas, agrupada por categoria em ordem alfabética; e a disponibilidade aparece como Sim ou Não nas telas. **Verificado:** CA-12, CA-13 e CA-14 passam (testes `test_ca12_*`, `test_ca13_*` e `test_ca14_*`), a migração foi aplicada sem perda ao `estoque.db` em uso, e as telas foram conferidas no navegador em desktop e celular.

### Sprint 9 — Exclusão lógica de categorias (planejada; pedido explícito, amplia o escopo)
Decisões do dono do projeto: (a) categoria **com materiais ativos não pode ser excluída** (bloqueio com `409` informando quantos); (b) só o **estoquista** exclui; (c) o **nome é liberado** para nova categoria; (d) **sem restauração** pela interface.
1. **Service e API.** Nova coluna `excluido_em` em `categorias`, pela migração leve (`COLUNAS_NOVAS`). Nova ação `EXCLUIR_CATEGORIA` (estoquista). `DELETE /categorias/{id}`: inexistente ou já excluída → `404`; com materiais ativos → `409` com `materiais` (inteiro) e nada gravado; sem materiais, marca `excluido_em`. **Liberar o nome:** o `UNIQUE` de `categorias.nome` não sai com `ALTER TABLE`; por isso, ao excluir, o nome guardado vira `"<nome> [excluída #id]"` (migração leve, sem recriar tabela). A unicidade por `casefold` passa a olhar **só categorias ativas**. Categoria excluída some de `GET /categorias`, `GET /saldos`, da validação em `POST /materiais` (→ `422`), do filtro `?categoria_id=` (→ `404`), da edição (→ `404`) e do seed (que não recria categorias do seed excluídas só por faltarem: ver dúvida abaixo).
2. **Telas.** Na lista de categorias do Cadastro, botão **Excluir** (só com a permissão) e `<dialog>` de confirmação; com materiais, a tela mostra a mensagem do `409`.
3. **Fechamento:** testes CA-15 e CA-16, documentação (README, `docs/`, visão do produto) e este arquivo.
- **Dúvida a resolver na parte 1:** o seed recria Papelaria, Escrita e Informática se não existirem; como o nome foi liberado, uma categoria do seed excluída **voltaria no próximo início**. Proposta: o seed só roda quando a tabela está vazia (inclusive de excluídas).
- Fora desta sprint: restaurar categoria excluída.
- **Pronto quando:** o estoquista exclui uma categoria sem materiais pela tela; com materiais, é bloqueado e vê quantos; a categoria some de todo o sistema e o nome pode ser reutilizado; o banco existente é migrado sem perda.

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

Excluir categorias (a edição do nome é a Sprint 5; a exclusão **lógica** é a Sprint 9, ainda não implementada) e restaurar categoria excluída. Saldo em data passada e extrato de movimentações por material (a Sprint 6 trata só do saldo atual). Restaurar um material excluído (a exclusão lógica da Sprint 8 só marca o registro no banco).

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

O banco é o arquivo `estoque.db`, criado na raiz ao iniciar o app, junto com o seed das categorias. As tabelas novas são criadas sozinhas e, desde a Sprint 8, uma **migração leve** (`app/migracoes.py`) acrescenta ao iniciar as colunas novas que faltam em tabelas existentes (regra 18). Antes de atualizar o código com um `estoque.db` que importa, **copie o arquivo**. Mudanças além de acrescentar colunas exigem recriar o banco ou alterar a tabela à mão.

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
- [x] Categorias poderão ser criadas pela interface ou só via seed? → **Pela interface**, além do seed. **Editar o nome** entra na Sprint 5; **excluir** continua fora do escopo
- [x] Nome de categoria diferencia maiúsculas de minúsculas? → **Não**: "Escrita" é igual a "escrita" (criação e edição); acentos continuam diferenciando
- [x] A regra "informar antes de alterar quantos registros serão afetados" vale para qual edição? → **Só a edição de categoria** (Sprint 5)
- [x] Quem edita categorias? → **Só o estoquista** (nova ação `EDITAR_CATEGORIA`)
- [x] O que é a "visão de consulta de saldo"? → **Resumo por categoria + saldo por material** (Sprint 6); saldo em data passada e extrato de movimentações ficam de fora
- [x] Em que rota fica a página de saldos? → **`/estoque/saldos`**, porque `/saldos` é a API
- [x] A visão de saldos mostra categorias sem materiais? → **Sim, com zeros** (diferente da Pesquisa, que as oculta); o total geral também vem do servidor
- [x] Formato do documento de visão do produto? → **Markdown em `docs/visao-do-produto.md`** (Sprint 7)
- [x] Quem lê o documento de visão? → **Equipe e donos do produto**
- [x] Que contexto o documento descreve? → **Genérico, um escritório** (sem organização específica)
- [x] Métricas de sucesso do documento? → **Propostas como hipóteses**, sem metas numéricas inventadas
- [x] O documento tem "Próximos passos"? → **Não**: descreve só o que existe hoje
- [x] A exclusão de material é física ou lógica? → **Lógica** (Sprint 8): o registro fica no banco, marcado como excluído; as movimentações antigas continuam guardadas
- [x] Quem exclui material? → **Só o estoquista** (nova ação `EXCLUIR_MATERIAL`)
- [x] O que fazer ao excluir material com saldo maior que zero? → **Permitir, com confirmação que mostra o saldo** (o servidor também exige)
- [x] Como o banco já existente ganha a coluna da exclusão lógica? → **Migração leve automática ao iniciar** (`ALTER TABLE ... ADD COLUMN`, idempotente, sem tocar nos dados); recomenda-se copiar o `estoque.db` antes
- [x] Qual tela é o "resumo de categoria" e como fica? → **Saldos**: a tabela única de materiais (Material | Quantidade | Categoria | Disponível), agrupada por categoria em ordem alfabética, substitui o resumo e o detalhe; os cartões do total geral continuam
- [x] Há uma coluna antes de "Material"? → **Não** (as colunas seguem a ordem listada, sem coluna extra)
- [x] Onde a disponibilidade vira "Sim"/"Não"? → **Em todas as telas** (Pesquisa, Saldos e filtros); **a API não muda**
- [x] Haverá login em versão futura (impacta registrar "quem retirou")? → ~~Ignorar no MVP~~ **Superado na Sprint 4**: login por CPF + senha
- [x] Como o usuário se identifica? → **CPF + senha**
- [x] O estoquista também movimenta e pesquisa? → **Não**: só o descrito (cadastros, valores de estoque e consulta, ver matriz na seção 4)
- [x] Quem mantém os usuários? → **Novo perfil Administrador** (fora das duas permissões originais)
- [x] Como remover um usuário? → **Inativar**
- [x] Segurança das senhas no protótipo? → **Simplificada**: senhas de 6+ caracteres, senha padrão `123456` e administrador padrão (CPF `529.982.247-25`). **Rever antes de uso real** (tamanho mínimo, senha padrão, administrador no código, chave de sessão)
- [ ] Registrar **quem** fez cada entrada e saída (`usuario_id` em `Movimentacao`)? Foi sugerido na Sprint 4, **não foi implementado**; exige acrescentar uma coluna (`usuario_id`) em `movimentacoes`, o que a migração leve da regra 18 comportaria
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