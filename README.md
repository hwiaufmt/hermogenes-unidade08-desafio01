# Controle de Materiais de Escritório

Aplicação web para controlar o estoque de materiais de escritório (papelaria, escrita, informática etc.): cadastrar materiais por categoria, registrar entradas e saídas, consultar o saldo atualizado e controlar **quem pode fazer o quê**, com login e três perfis de usuário.

Este é um **MVP** que valida o ciclo *cadastrar → entrada → saída → consultar saldo*, com regras de negócio confiáveis.

## Funcionalidades

- **Categorias:** seed inicial (Papelaria, Escrita, Informática), criação de novas e **edição do nome** pela interface. O nome é único sem diferenciar maiúsculas de minúsculas ("Escrita" = "escrita"). Ao editar uma categoria que tem materiais, o sistema **informa quantos registros serão afetados** e só grava depois da confirmação.
- **Cadastro de material:** exige categoria válida; estoque inicial e estoque mínimo opcionais (padrão 0).
- **Entrada e saída:** a entrada soma ao saldo; a saída subtrai e é **bloqueada** se o saldo for insuficiente.
- **Status automático:** saldo 0 → **Indisponível**; qualquer outro → **Disponível**. Não há campo editável. Nas telas, a disponibilidade aparece como **Sim** ou **Não** (a API continua devolvendo `status`).
- **Exclusão lógica de material:** o estoquista exclui um material pela Pesquisa (com confirmação quando há saldo). Ele some de todas as telas e totais, mas o registro e as movimentações continuam no banco. Não há restauração pela interface.
- **Pesquisa:** materiais e saldos agrupados por categoria, com busca por nome e filtros de categoria e disponibilidade (Sim/Não).
- **Saldos:** visão de leitura com o **total geral** e uma tabela **Material | Quantidade | Categoria | Disponível**, agrupada por categoria em ordem alfabética, tudo calculado no servidor.
- **Usuários:** nome, **CPF único** e e-mail; cadastrar, editar, inativar e reativar.
- **Login e perfis:** entrada por CPF e senha; três perfis com permissões diferentes (tabela abaixo).
- Cada entrada e saída grava uma movimentação (tipo, quantidade, saldo após, data UTC) na mesma transação do saldo.

## Perfis e permissões

| Ação | Estoquista | Operador | Administrador |
|---|---|---|---|
| Criar categoria | ✅ | | |
| Editar categoria (com aviso de impacto) | ✅ | | |
| Cadastrar material (estoque inicial e mínimo) | ✅ | | |
| Excluir material (exclusão lógica) | ✅ | | |
| Pesquisar / consultar estoque e saldos | ✅ | ✅ | |
| Movimentar (entrada e saída) | | ✅ | |
| Manter usuários | | | ✅ |

As permissões valem **na API e nas telas**: sem login a API responde `401`, e sem permissão `403`. A matriz fica em [`app/permissoes.py`](app/permissoes.py).

## Stack

Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2 com SQLite, Jinja2, HTML/CSS/JavaScript (ES modules, sem framework), sessão em cookie assinado (`itsdangerous`), pytest + httpx e ruff.

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

### Primeiro acesso

O sistema exige login. Ao iniciar com o banco **sem usuários**, ele cria sozinho o administrador padrão do protótipo:

| Campo | Valor |
|---|---|
| CPF | `529.982.247-25` (CPF de exemplo, com dígitos válidos) |
| Senha | `123456` |

```bash
uvicorn app.main:app --reload
```

Abra <http://localhost:8000>, entre com esse CPF e senha e, na tela **Usuários**, cadastre estoquistas e operadores. **Senha padrão:** quem for cadastrado sem senha informada fica com `123456`.

> Esta é uma configuração de **protótipo**, sem preocupação com segurança. Antes de qualquer uso real, troque as senhas e defina os dados do administrador pelas variáveis abaixo (por exemplo, `$env:ESTOQUE_ADMIN_CPF = "SEU-CPF"` no PowerShell, ou `export` no Linux/macOS).

| Variável | Para quê |
|---|---|
| `ESTOQUE_ADMIN_CPF`, `ESTOQUE_ADMIN_SENHA` | definem o primeiro administrador (padrão: o acima) |
| `ESTOQUE_ADMIN_NOME`, `ESTOQUE_ADMIN_EMAIL` | opcionais (padrão: `Administrador`, `administrador@estoque.local`) |
| `ESTOQUE_SECRET_KEY` | assina o cookie de sessão; sem ela, as sessões se perdem a cada reinício |

A documentação interativa da API fica em `/docs`. O banco é o arquivo `estoque.db`, criado na raiz ao iniciar, junto com o seed das categorias. Ao atualizar o código, tabelas novas são criadas sozinhas e uma **migração leve** (`app/migracoes.py`) acrescenta ao iniciar as colunas novas que faltam (hoje, `materiais.excluido_em`), sem alterar dados. Copie o `estoque.db` antes de atualizar; mudanças além de acrescentar colunas exigem recriar o banco.

## Como testar

```bash
pytest                          # testes (usam SQLite em memória)
ruff check . && ruff format .   # lint e formatação
```

Cada critério de aceite tem testes nomeados com o ID (`test_ca01_...` a `test_ca14_...`). Os testes de acesso conferem, para cada perfil e cada rota, se o resultado é permitido ou `403`, usando a matriz real.

## Páginas

| Rota | Descrição | Quem acessa |
|---|---|---|
| `/login` | **Entrar** com CPF e senha | público |
| `/` | leva cada perfil à sua primeira tela | logado |
| `/pesquisa` | **Pesquisa:** saldos agrupados por categoria, com busca, filtros e botão Excluir (estoquista) | estoquista, operador |
| `/estoque/saldos` | **Saldos:** total geral e tabela Material, Quantidade, Categoria e Disponível, agrupada por categoria | estoquista, operador |
| `/movimentar` | **Movimentar:** registrar entrada ou saída e ver o saldo | operador |
| `/materiais/novo` | **Cadastro:** novo material, nova categoria e lista de categorias com edição | estoquista |
| `/gestao/usuarios` | **Usuários:** cadastrar, editar, inativar e reativar | administrador |

Sem login, as páginas redirecionam para `/login`. Sem permissão, mostram "Acesso negado" (`403`).

## API

| Método e rota | Descrição | Erros |
|---|---|---|
| `POST /login` | Entra com `{"cpf", "senha"}` | `401` CPF ou senha inválidos |
| `POST /logout` | Encerra a sessão | |
| `GET /me` | Usuário logado | `401` |
| `GET /categorias` | Lista as categorias, com `total_materiais` de cada uma | `401`, `403` |
| `POST /categorias` | Cria categoria (`nome` único, **sem diferenciar maiúsculas de minúsculas**) | `422` vazio ou duplicado |
| `PUT /categorias/{id}` | Altera o nome. Com materiais, exige `confirmar: true` | `404`, `422` vazio ou duplicado, `409` sem confirmação (informa `afetados`) |
| `GET /materiais` | Lista materiais; filtros `?categoria_id=`, `?q=`, `?status=` | `404` categoria inexistente, `422` status inválido |
| `GET /materiais/{id}` | Consulta um material | `404` |
| `DELETE /materiais/{id}?confirmar=true` | Exclusão lógica; com saldo maior que zero exige `confirmar=true` | `404`, `409` sem confirmação (informa `saldo`) |
| `GET /saldos` | Totais por categoria e geral, com o saldo de cada material | `401`, `403` |
| `POST /materiais` | Cadastra material | `422` categoria ausente/inválida, valores inválidos |
| `POST /materiais/{id}/entrada` | Soma `quantidade` ao saldo | `404`, `422` |
| `POST /materiais/{id}/saida` | Subtrai `quantidade` do saldo | `404`, `422`, `409` saldo insuficiente |
| `GET/POST /usuarios`, `GET/PUT /usuarios/{id}` | Mantém usuários | `409` CPF duplicado, `422` CPF/e-mail/senha inválidos |
| `POST /usuarios/{id}/inativar` e `/reativar` | Inativa ou reativa | `409` último administrador |

Todas as rotas, exceto `POST /login`, exigem login (`401`) e a permissão do perfil (`403`). Entrada e saída recebem `{"quantidade": n}` (inteiro maior que zero) e devolvem o material atualizado, com `quantidade` e `status`. As mensagens de erro das operações, inclusive as de validação (`422`), vêm em português no campo `detail`, como texto. A exceção são as respostas padrão do framework para endereços inexistentes (`404 "Not Found"`) e métodos não permitidos (`405 "Method Not Allowed"`), que saem em inglês.

## Regras de negócio

- Quantidade de entrada e saída: inteiro maior que zero.
- O saldo nunca fica negativo.
- A verificação de saldo e a subtração na saída são **atômicas** (`UPDATE ... WHERE quantidade >= :qtd`).
- Saldo e movimentação são gravados na mesma transação (tudo ou nada).
- `estoque_minimo` é guardado e exibido; não dispara alerta no MVP.
- O nome da categoria é único **sem diferenciar maiúsculas de minúsculas**; acentos diferenciam.
- Alterar o nome de uma categoria com materiais exige confirmação: sem ela o servidor responde `409`, diz quantos registros seriam afetados e não grava.
- Material excluído (exclusão lógica) não aparece em nenhuma consulta, total ou movimentação (`404`); as movimentações antigas ficam guardadas. Com saldo maior que zero, a exclusão exige confirmação.
- O **CPF** é único (com dígitos verificadores válidos); CPF repetido, mesmo com máscara diferente, é recusado.
- A senha tem pelo menos 6 caracteres (protótipo; a senha padrão é `123456`) e é guardada só como hash `scrypt`.
- Usuários são **inativados**, não apagados. O último administrador ativo não pode ser inativado nem rebaixado.
- Inativar um usuário ou mudar o perfil dele vale na próxima requisição, mesmo com a sessão aberta.

## Estrutura

```
app/
├── main.py            # criação do app, middleware, routers, seed, admin inicial
├── config.py          # chave da sessão e variáveis do administrador inicial
├── database.py        # engine, sessão, Base
├── models.py          # Categoria, Material, Movimentacao, Usuario
├── schemas.py         # modelos Pydantic
├── seguranca.py       # hash de senha
├── permissoes.py      # matriz perfil -> ações
├── dependencias.py    # usuario_atual, exigir(*acoes)
├── erros.py           # mensagens de validação em português
├── services/          # estoque.py e usuarios.py (regras de negócio)
├── routers/           # autenticacao, categorias, materiais, movimentacoes, usuarios, paginas
├── templates/         # base, login, acesso_negado, pesquisa, movimentar, cadastro, usuarios
└── static/            # css e js (o JS só chama a API e renderiza)
docs/                  # guia de uso, API, arquitetura
tests/                 # um arquivo por área; conftest.py com os fixtures de login
```

Camadas: router (HTTP) → service (regra de negócio) → models (dados). Nenhuma regra de negócio fica nos routers nem no JavaScript, e quem pode o quê fica só na matriz de permissões.

## Documentação

- [Visão do produto](docs/visao-do-produto.md): o que o produto é, para quem serve, o que faz hoje, o que não faz e os riscos do protótipo.
- [Guia de uso](docs/guia-de-uso.md): como usar as telas, por perfil.
- [Referência da API](docs/api.md): rotas, corpos, respostas e mensagens de erro.
- [Arquitetura](docs/arquitetura.md): camadas, modelo de dados, autenticação, permissões e decisões de integridade.

## Fora do escopo

Aprovação de requisições, fornecedores e notas fiscais, relatórios e dashboards, notificações, integrações, multi-filial, edição/exclusão de movimentações, exclusão de categorias, histórico em tela, exportação e indicador de estoque baixo.

Também fora do escopo por ora: troca e recuperação de senha pelo próprio usuário, limite de tentativas de login, edição de CPF e registrar **quem** fez cada movimentação.

Mais detalhes de contexto e decisões do projeto estão em [`claude.md`](claude.md).
