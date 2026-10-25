# Arquitetura

Visão técnica do **Controle de Materiais de Escritório**: camadas, modelo de dados, autenticação e permissões, fluxo de uma operação e decisões de integridade.

## Camadas

```
Navegador (HTML + JS)  ──fetch──►  routers  ──►  services  ──►  models  ──►  SQLite
                                      │
                       dependencias (login) + permissoes (matriz)
```

| Camada | Arquivos | Responsabilidade |
|---|---|---|
| Interface | `app/templates/`, `app/static/` | Renderiza telas e chama a API. **Não calcula saldo nem status.** |
| Routers | `app/routers/` | Recebem HTTP, validam o formato (Pydantic), chamam o service e convertem exceções de domínio em códigos HTTP. **Sem regra de negócio.** |
| Acesso | `app/dependencias.py`, `app/permissoes.py` | Identificam o usuário da sessão e verificam se o perfil tem a ação exigida pela rota ou pela página. |
| Service | `app/services/estoque.py`, `app/services/usuarios.py` | Regras de negócio: entrada, saída, status, busca, categorias, materiais, CPF, login e regras de usuários. |
| Dados | `app/models.py`, `app/database.py` | Modelos SQLAlchemy, engine e sessão. |
| Validação | `app/schemas.py`, `app/erros.py` | Schemas de entrada e saída; tradução das mensagens de validação para português. |
| Segurança | `app/seguranca.py`, `app/config.py` | Hash de senha (scrypt); chave e duração da sessão; variáveis do administrador inicial. |

### Módulos

- **`main.py`**: cria o app, registra o `SessionMiddleware`, os routers, os arquivos estáticos e os tratadores de erro. No startup cria as tabelas, aplica o seed das categorias e cria o administrador inicial.
- **`routers/autenticacao.py`**: `POST /login`, `POST /logout` e `GET /me`.
- **`routers/categorias.py`**: `GET` e `POST /categorias`.
- **`routers/materiais.py`**: `GET /materiais` (com `categoria_id`, `q` e `status`), `GET /materiais/{id}` e `POST /materiais`.
- **`routers/movimentacoes.py`**: `POST /materiais/{id}/entrada` e `.../saida`.
- **`routers/usuarios.py`**: `/usuarios` (listar, consultar, criar, atualizar, inativar e reativar).
- **`routers/paginas.py`**: telas HTML, menu por perfil e guarda de páginas. Fora da documentação OpenAPI.
- **`erros.py`**: tratador global de `RequestValidationError`. Devolve `422` com `detail` em texto, em português.
- **`permissoes.py`**: o enum `Acao`, a matriz `PERMISSOES` (perfil → ações) e `perfil_pode(perfil, *acoes)`.
- **`dependencias.py`**: `usuario_da_sessao`, `usuario_atual` (exige login) e `exigir(*acoes)` (exige login e permissão).

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

usuarios (independente das tabelas acima)
─────────
id (PK)
nome
cpf (único, só dígitos)
email
perfil ('administrador' | 'estoquista' | 'operador')
senha_hash (scrypt com sal)
ativo
```

- O **status não é armazenado**: é calculado por `calcular_status(quantidade)` (`0` → "Indisponível", senão "Disponível") e exposto como campo de leitura nas respostas.
- Restrições no banco (`CHECK`): `quantidade >= 0` e `estoque_minimo >= 0` em materiais; `tipo` restrito e `quantidade > 0` em movimentações; `perfil` restrito em usuários.
- `movimentacoes` serve para rastreabilidade. Não há tela nem endpoint de histórico no MVP, e **a tabela não registra qual usuário fez a movimentação** (decisão em aberto no `claude.md`).
- Não há migração: tabelas novas são criadas por `create_all`, mas colunas novas em tabelas existentes exigem recriar o banco.

## Autenticação

1. `POST /login` recebe CPF e senha. O service `autenticar` busca o usuário pelo CPF normalizado e **sempre** calcula o hash (contra um hash falso se o CPF não existe), para o tempo de resposta não revelar quais CPFs existem.
2. CPF inexistente, senha errada e usuário inativo levantam o mesmo `CredenciaisInvalidasError` → `401 "CPF ou senha inválidos."`.
3. Com sucesso, a sessão anterior é limpa e `usuario_id` é gravado na sessão: um **cookie assinado** (`SessionMiddleware`, `itsdangerous`), `HttpOnly`, `SameSite=Lax`, válido por 8 horas. Não há tabela de sessões.
4. **A cada requisição** a dependência relê o usuário no banco. Como o cookie só guarda o id, inativar um usuário ou mudar o perfil dele vale na próxima chamada, mesmo com o cookie ainda válido.
5. A senha é guardada como `scrypt$n$r$p$sal$hash` (biblioteca padrão), com sal aleatório; a verificação usa comparação em tempo constante.

**Simplificações do protótipo:** a senha mínima é de 6 caracteres; um usuário cadastrado sem senha recebe a senha padrão `123456` (`config.SENHA_PADRAO`); e, em banco sem usuários, o início do app cria o administrador padrão (CPF `529.982.247-25`, senha `123456`), a menos que `ESTOQUE_ADMIN_CPF` e `ESTOQUE_ADMIN_SENHA` definam outro. O log avisa quando a senha do administrador é a padrão.

A chave de assinatura vem de `ESTOQUE_SECRET_KEY`. Sem ela, uma chave aleatória é gerada a cada início e as sessões não sobrevivem a reinícios. O cookie não tem a flag `Secure` (funciona em `http://localhost`); em HTTPS, ligue `https_only`.

## Permissões

A matriz `PERMISSOES` em `app/permissoes.py` liga cada perfil a um conjunto de ações:

| Ação | Estoquista | Operador | Administrador |
|---|---|---|---|
| `criar_categoria` | ✅ | | |
| `cadastrar_material` | ✅ | | |
| `consultar_estoque` | ✅ | ✅ | |
| `movimentar` | | ✅ | |
| `gerir_usuarios` | | | ✅ |

Ela é a **única fonte de verdade** de quem pode o quê. Três consumidores a leem:

- **API:** cada rota declara `dependencies=[Depends(exigir(Acao.X, ...))]`. Sem login → `401`; sem permissão → `403`. `exigir` aceita **qualquer uma** das ações listadas, o que permite que a lista de materiais sirva à Pesquisa e à tela Movimentar, e que `GET /categorias` sirva aos formulários de cadastro.
- **Páginas:** `acesso_pagina(...)` redireciona para `/login` (`303`) sem login e mostra "Acesso negado" (`403`) sem permissão.
- **Menu:** `menu_do_usuario` filtra os itens pela mesma matriz; a raiz `/` leva cada perfil à primeira tela do seu menu.

Perfil ausente da matriz, ou com conjunto vazio, não pode nada (falha segura). Um teste garante que todo perfil existente tem uma entrada.

### Páginas e rotas com o mesmo caminho

A tela de usuários fica em `/gestao/usuarios` porque `/usuarios` é a API e responderia primeiro, devolvendo JSON ao navegador. Do mesmo modo, as rotas da API usam `{id:int}` para não capturar `/materiais/novo`.

## Fluxo de uma saída

1. A tela **Movimentar** envia `POST /materiais/{id}/saida` com `{"quantidade": n}`.
2. A dependência `exigir(Acao.MOVIMENTAR)` confere login e permissão (`401`/`403`).
3. O schema `MovimentacaoCriar` exige inteiro estrito maior que zero. Se falhar, `erros.py` devolve `422` em português.
4. O router chama `registrar_saida(db, id, n)`.
5. O service executa **um único `UPDATE`** com a condição de saldo:
   `UPDATE materiais SET quantidade = quantidade - :n WHERE id = :id AND quantidade >= :n RETURNING quantidade`
6. Sem linha afetada: o material não existe (`MaterialInexistenteError` → `404`) ou o saldo é insuficiente (`SaldoInsuficienteError` → `409`). Há `rollback`, então nada é gravado.
7. Com sucesso: grava a `Movimentacao` com o `saldo_apos` e faz `commit`. Saldo e movimentação saem na **mesma transação**.
8. O router devolve o material atualizado, com `quantidade` e `status`.

A entrada segue o mesmo caminho, com `quantidade = quantidade + :n`.

## Busca de materiais

`listar_materiais(db, categoria_id, busca, status)` monta uma consulta única: o filtro de categoria valida a existência da categoria; `busca` usa `lower(nome) LIKE` com escape de `%` e `_`; `status` vira `quantidade = 0` ou `quantidade > 0`. O JavaScript só envia os parâmetros e renderiza o resultado, agrupando por categoria para exibir.

## Decisões de integridade

| Regra | Como é garantida |
|---|---|
| Saldo nunca negativo | Condição `quantidade >= :n` no `UPDATE` e `CHECK` no banco |
| Sem saída dupla concorrente | Verificação e subtração atômicas no mesmo `UPDATE` |
| Tudo ou nada | Saldo e movimentação no mesmo `commit`; `rollback` em qualquer falha |
| Categoria obrigatória e válida | Verificada em `criar_material` antes de gravar |
| Categoria única | Índice único em `categorias.nome`; `IntegrityError` vira `CategoriaDuplicadaError` |
| Quantidade inteira positiva | Validação no schema e, de novo, no service |
| CPF único | Índice único em `usuarios.cpf` (só dígitos); `IntegrityError` vira `CpfDuplicadoError` |
| CPF válido | Dígitos verificadores conferidos no schema; valor guardado só com dígitos |
| Sempre há quem gerencie usuários | O último administrador ativo não pode ser inativado nem rebaixado (`UltimoAdministradorError`) |
| Nada de senha em claro | Só o hash `scrypt` é guardado; nenhuma resposta devolve senha ou hash |

## Exceções de domínio

Definidas em `services/estoque.py` e `services/usuarios.py` e convertidas em HTTP nos routers:

| Exceção | HTTP |
|---|---|
| `CategoriaInexistenteError` | `422` ao cadastrar material; `404` ao filtrar a listagem |
| `CategoriaDuplicadaError` | `422` |
| `MaterialInexistenteError` | `404` |
| `SaldoInsuficienteError` | `409` |
| `QuantidadeInvalidaError` | defesa do service; na API o schema responde antes, com `422` |
| `UsuarioInexistenteError` | `404` |
| `CpfDuplicadoError` | `409` |
| `UltimoAdministradorError` | `409` |
| `CredenciaisInvalidasError` | `401` |

## Interface web

Módulos ES, sem framework e sem variáveis globais:

- **`api.js`**: `requisitar`, `enviarJson`, `mostrarMensagem` e a leitura de mensagens de erro da API. Uma resposta `401` (fora do login) leva a `/login`, para o caso de a sessão cair com a página aberta.
- **`login.js`** e **`sair.js`**: entrar e sair. Depois de entrar, `/` leva à primeira tela do perfil.
- **`pesquisa.js`**: carrega categorias e materiais, envia busca, categoria e status à API (a busca por nome espera 250 ms depois da digitação), **agrupa por categoria para exibir** e mostra um resumo.
- **`movimentar.js`**: lista materiais, mostra o saldo vindo da API e registra a movimentação.
- **`cadastro.js`**: cadastra material e cria categoria, atualizando a lista de categorias.
- **`usuarios.js`**: lista, cadastra, edita (CPF travado, senha opcional), inativa e reativa usuários.

O menu e o nome do usuário vêm renderizados pelo servidor (`base.html`), já filtrados pelo perfil.

Acessibilidade: HTML semântico, `label` em todo campo, link "Pular para o conteúdo", foco visível, regiões `aria-live` para mensagens, tabelas rolagem-focáveis e selo de status com texto e ícone (não depende só da cor). Alvos de toque de 44px e contraste conferido (campos 4,6:1).

## Testes

`pytest` com `TestClient` e SQLite **em memória** isolado por teste (`tests/conftest.py`).

Fixtures principais:

- `cliente_anonimo`: cliente sem login.
- `entrar_como(perfil)`: cria um usuário de teste do perfil e entra.
- `client`: cliente logado com **todas** as permissões. Os testes de regra de negócio o usam para não depender da matriz.

| Arquivo | Cobre |
|---|---|
| `test_cadastro.py` | CA-01, valores inválidos, filtro por categoria |
| `test_categorias.py` | listar o seed, criar, duplicada, vazia |
| `test_entrada.py` | CA-02 e entradas inválidas |
| `test_saida.py` | CA-03, CA-04 e saídas inválidas |
| `test_estoque.py` | CA-05, CA-06 e registro das movimentações |
| `test_pesquisa.py` | busca por nome, status e combinações de filtros |
| `test_erros.py` | mensagens de validação em português |
| `test_fluxo_completo.py` | ciclo completo de ponta a ponta |
| `test_usuarios.py` | CA-07 (CPF único), validações, CRUD, inativação, último administrador |
| `test_login.py` | login, logout, sessão, cookie adulterado e flags do cookie |
| `test_administrador_inicial.py` | criação única do primeiro administrador |
| `test_permissoes.py` | o mecanismo `exigir`, com matriz de teste própria |
| `test_acesso_rotas.py` | CA-08: cada perfil × cada rota da API, com a **matriz real** |
| `test_paginas.py` | CA-08 nas telas: redirecionamento, "Acesso negado", menu por perfil |

O JavaScript não tem testes automatizados; foi conferido manualmente no navegador (desktop e celular) com os três perfis.
