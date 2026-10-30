# Referência da API

API REST em JSON. Com o app rodando, a documentação interativa (Swagger) fica em <http://localhost:8000/docs>. Para o contexto do produto, veja a [visão do produto](visao-do-produto.md).

## Convenções

- Corpo e respostas em `application/json`.
- Erros devolvem `{"detail": "mensagem em português"}`. O `detail` é sempre **texto**, inclusive nos `422` de validação.
- **Exceção:** endereços que não existem (`404`) e métodos não permitidos (`405`) respondem com a mensagem padrão do framework, em inglês: `{"detail": "Not Found"}` e `{"detail": "Method Not Allowed"}`. A documentação interativa (`/docs`) também é em inglês.
- Quando há mais de um problema de validação, as mensagens vêm unidas num só texto.

### Autenticação e permissões

- Todas as rotas, exceto `POST /login`, exigem **login**. A sessão é um cookie assinado (`HttpOnly`, `SameSite=Lax`, válido por 8 horas) que o servidor define no `POST /login`; clientes HTTP precisam reenviá-lo.
- Cada rota exige uma **ação** que o perfil do usuário deve ter (campo "Permissão" de cada rota). Perfis e ações: [matriz de permissões](#matriz-de-permissões).
- O usuário é relido do banco a cada requisição: inativar alguém ou mudar o perfil dele vale imediatamente.

### Códigos de erro

| Código | Quando |
|---|---|
| `401` | sem login, sessão inválida/expirada, usuário inativo; ou CPF/senha errados no login |
| `403` | logado, mas o perfil não tem a permissão da rota |
| `404` | material, categoria ou usuário inexistente |
| `409` | saldo insuficiente para a saída; CPF de usuário já cadastrado; inativar ou rebaixar o último administrador; alterar categoria com materiais sem confirmação (a resposta traz também `afetados`); excluir material com saldo sem confirmação (a resposta traz também `saldo`) |
| `422` | dado inválido: campo ausente, tipo errado, valor fora do limite, categoria inválida, nome duplicado, CPF/e-mail/perfil/senha inválidos, filtro de status inválido |

### Objetos

**Categoria**

```json
{ "id": 1, "nome": "Papelaria" }
```

**Material**

```json
{
  "id": 3,
  "nome": "Resma A4",
  "categoria": { "id": 1, "nome": "Papelaria" },
  "quantidade": 10,
  "estoque_minimo": 2,
  "status": "Disponível"
}
```

`status` é calculado pelo servidor: `"Indisponível"` quando `quantidade` é 0, senão `"Disponível"`. As telas mostram essa informação como **Sim** (`"Disponível"`) ou **Não** (`"Indisponível"`); é só o rótulo na tela, e a API continua devolvendo `status`.

Material excluído (exclusão lógica) não aparece em nenhuma rota de leitura nem de movimentação; consultá-lo ou movimentá-lo dá `404`.

**Usuário**

```json
{
  "id": 2,
  "nome": "Maria Silva",
  "cpf": "52998224725",
  "email": "maria@exemplo.com",
  "perfil": "estoquista",
  "ativo": true
}
```

O `cpf` vem só com dígitos. A senha e o hash **nunca** são devolvidos.

### Matriz de permissões

| Ação | Estoquista | Operador | Administrador |
|---|---|---|---|
| `criar_categoria` | ✅ | | |
| `editar_categoria` | ✅ | | |
| `cadastrar_material` | ✅ | | |
| `excluir_material` | ✅ | | |
| `consultar_estoque` (inclui `GET /saldos`) | ✅ | ✅ | |
| `movimentar` | | ✅ | |
| `gerir_usuarios` | | | ✅ |

A matriz fica em `app/permissoes.py`. Quando uma rota aceita "qualquer uma de" várias ações, basta o perfil ter uma delas.

---

## Autenticação

### `POST /login`

Abre a sessão. **Permissão:** nenhuma (rota pública).

**Corpo**

```json
{ "cpf": "529.982.247-25", "senha": "senha-segura-1" }
```

O CPF aceita máscara. A sessão anterior, se houver, é substituída.

| Resposta | Descrição |
|---|---|
| `200` | o usuário logado (objeto Usuário) e o cookie de sessão |
| `401` | `"CPF ou senha inválidos."` (CPF inexistente, senha errada e usuário inativo recebem a **mesma** resposta) |
| `422` | campo ausente, por exemplo `"O campo 'senha' é obrigatório."` |

### `POST /logout`

Encerra a sessão. **Permissão:** nenhuma. Responde `204` mesmo sem login.

### `GET /me`

Devolve o usuário da sessão. **Permissão:** apenas estar logado.

| Resposta | Descrição |
|---|---|
| `200` | o usuário logado |
| `401` | `"É necessário entrar no sistema."` |

---

## Categorias

### `GET /categorias`

**Permissão:** `consultar_estoque`, `cadastrar_material`, `criar_categoria` ou `editar_categoria` (qualquer uma).

Lista as categorias em ordem alfabética, com **quantos materiais cada uma tem** (`total_materiais`). Já vem com Papelaria, Escrita e Informática.

**200**

```json
[
  { "id": 2, "nome": "Escrita", "total_materiais": 3 },
  { "id": 3, "nome": "Informática", "total_materiais": 0 },
  { "id": 1, "nome": "Papelaria", "total_materiais": 1 }
]
```

### `POST /categorias`

**Permissão:** `criar_categoria`.

Cria uma categoria.

**Corpo**

```json
{ "nome": "Limpeza" }
```

O nome é aparado (espaços nas pontas são removidos). Deve ser único **sem diferenciar maiúsculas de minúsculas**: "Escrita" e "escrita" são o mesmo nome. Acentos diferenciam ("Informatica" não é "Informática").

| Resposta | Descrição |
|---|---|
| `201` | a categoria criada (`id` e `nome`) |
| `422` | `"O nome da categoria é obrigatório."` (vazio ou só espaços) |
| `422` | `"Já existe uma categoria chamada 'Limpeza'."` (mesmo que você tenha digitado `limpeza`; a mensagem mostra o nome que já existe) |

### `PUT /categorias/{id}`

**Permissão:** `editar_categoria`.

Altera o **nome** da categoria. As mesmas regras de nome da criação valem aqui (aparado, único sem diferenciar maiúsculas de minúsculas).

**Corpo**

```json
{ "nome": "Escritório", "confirmar": false }
```

`confirmar` é opcional (padrão `false`). Quando a categoria **tem materiais**, a alteração só é gravada com `"confirmar": true`: sem isso o servidor **não grava** e informa quantos registros seriam afetados. Quando a categoria não tem materiais, grava direto, com ou sem `confirmar`.

| Resposta | Descrição |
|---|---|
| `200` | a categoria atualizada, com `total_materiais` |
| `404` | `"A categoria 99 não existe."` |
| `409` | precisa de confirmação (ver abaixo) |
| `422` | `"O nome da categoria é obrigatório."` |
| `422` | `"Já existe uma categoria chamada 'Papelaria'."` (nome repetido, em qualquer caixa; é recusado **antes** de pedir confirmação) |
| `422` | `"Valor inválido no campo 'confirmar'."` |

**`409` de confirmação**

```json
{
  "detail": "Esta categoria tem 3 materiais; a mudança de nome afetará 3 registros. Confirme para gravar.",
  "afetados": 3
}
```

Além do `detail` em texto, esta resposta traz `afetados`, o número de materiais da categoria. Para gravar, repita a chamada com `"confirmar": true`.

Manter o mesmo nome não altera nada e não pede confirmação. Mudar só a caixa do próprio nome ("Limpeza" → "LIMPEZA") é permitido e, se a categoria tem materiais, pede confirmação como qualquer outra mudança de nome.

---

## Materiais

### `GET /materiais`

**Permissão:** `consultar_estoque` ou `movimentar` (qualquer uma).

Lista os materiais em ordem alfabética de nome. Os filtros se combinam.

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `categoria_id` | inteiro, opcional | só os materiais dessa categoria |
| `q` | texto, opcional | parte do nome, sem diferenciar maiúsculas de minúsculas (vazio não filtra; `%` e `_` valem como texto) |
| `status` | `Disponível` ou `Indisponível`, opcional | só os materiais com esse status |

| Resposta | Descrição |
|---|---|
| `200` | lista de materiais (vazia se nada atende aos filtros) |
| `404` | `"A categoria 99 não existe."` (filtro com categoria inexistente) |
| `422` | `"Valor inválido no campo 'status'."` |

A comparação de maiúsculas e minúsculas em `q` é garantida para letras ASCII; letras acentuadas podem não casar entre maiúscula e minúscula (limitação do `lower()` do SQLite).

### `GET /materiais/{id}`

**Permissão:** `consultar_estoque` ou `movimentar` (qualquer uma).

Consulta um material.

| Resposta | Descrição |
|---|---|
| `200` | o material |
| `404` | `"O material 99 não existe."` |

### `POST /materiais`

**Permissão:** `cadastrar_material`.

Cadastra um material. Só grava se a categoria existir.

**Corpo**

| Campo | Tipo | Obrigatório | Regra |
|---|---|---|---|
| `nome` | texto | sim | não vazio (espaços nas pontas removidos) |
| `categoria_id` | inteiro | sim | deve existir |
| `quantidade` | inteiro | não (padrão 0) | ≥ 0, é o estoque inicial |
| `estoque_minimo` | inteiro | não (padrão 0) | ≥ 0; apenas guardado e exibido |

```json
{ "nome": "Resma A4", "categoria_id": 1, "quantidade": 10, "estoque_minimo": 2 }
```

| Resposta | Descrição |
|---|---|
| `201` | o material criado. Com `quantidade` 0 ele já nasce `"Indisponível"` |
| `422` | `"Selecione uma categoria."` (ausente ou nula) |
| `422` | `"A categoria 99 não existe."` |
| `422` | `"O nome do material é obrigatório."` |
| `422` | `"O campo 'quantidade' deve ser maior ou igual a 0."` (ou `'estoque mínimo'`) |
| `422` | `"O campo 'quantidade' deve ser um número inteiro."` |

### `DELETE /materiais/{id}`

**Permissão:** `excluir_material`.

Exclusão **lógica**: o material continua no banco com a data da exclusão (`excluido_em`) e as movimentações dele não são apagadas, mas ele deixa de aparecer em listagens, saldos, totais e movimentações. Não há rota para restaurar.

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `confirmar` | `true` ou `false`, opcional (padrão `false`) | obrigatório `true` quando o material tem saldo maior que zero |

| Resposta | Descrição |
|---|---|
| `204` | excluído, sem corpo |
| `404` | `"O material 99 não existe."` (inclui material já excluído) |
| `409` | precisa de confirmação (ver abaixo); nada é gravado |

**`409` de confirmação**

```json
{
  "detail": "O material 'Resma A4' tem 10 unidade(s) em estoque; ao excluir, ele deixa de aparecer no sistema. Confirme para excluir.",
  "saldo": 10
}
```

Com saldo 0, a exclusão é feita direto. Para excluir material com saldo, repita a chamada com `?confirmar=true`.

---

## Saldos

### `GET /saldos`

**Permissão:** `consultar_estoque`.

Devolve a consulta de saldos: os **totais por categoria**, o saldo de cada material e o **total geral**. Todos os números são calculados pelo servidor.

**200**

```json
{
  "categorias": [
    {
      "categoria": { "id": 2, "nome": "Escrita" },
      "total_materiais": 2,
      "total_unidades": 5,
      "total_indisponiveis": 1,
      "materiais": [
        { "id": 3, "nome": "Caneta azul", "quantidade": 5, "estoque_minimo": 0, "status": "Disponível" },
        { "id": 4, "nome": "Caneta preta", "quantidade": 0, "estoque_minimo": 0, "status": "Indisponível" }
      ]
    },
    {
      "categoria": { "id": 3, "nome": "Informática" },
      "total_materiais": 0,
      "total_unidades": 0,
      "total_indisponiveis": 0,
      "materiais": []
    }
  ],
  "totais": { "total_materiais": 2, "total_unidades": 5, "total_indisponiveis": 1 }
}
```

| Campo | Significado |
|---|---|
| `total_materiais` | quantos materiais a categoria tem |
| `total_unidades` | soma dos saldos (`quantidade`) dos materiais da categoria |
| `total_indisponiveis` | quantos materiais têm saldo 0 (status `"Indisponível"`) |
| `totais` | a soma dos três números acima em **todas** as categorias |

Regras:

- **Todas as categorias aparecem**, inclusive as sem materiais, com zeros e `materiais` vazio. (A Pesquisa, ao contrário, só mostra categorias com material.)
- Categorias e materiais vêm em **ordem alfabética sem diferenciar maiúsculas de minúsculas**.
- Os números acompanham as entradas e saídas: cada chamada reflete o saldo atual. Materiais excluídos não entram em nenhum número.
- A tela Saldos usa só o total geral (`totais`) e as listas de `materiais`, na ordem recebida (categoria e depois nome); os totais por categoria seguem na API, mas a tela não os exibe.
- Não há filtros nem paginação; para filtrar por nome, categoria ou status, use `GET /materiais`.
- Respostas de erro: `401` sem login e `403` para quem não tem `consultar_estoque` (o administrador).

---

## Movimentações

Entrada e saída recebem o mesmo corpo e devolvem o **material atualizado**. **Permissão** das duas: `movimentar`.

**Corpo**

```json
{ "quantidade": 3 }
```

`quantidade` deve ser um **inteiro maior que zero**. Texto (`"3"`) e decimais (`2.5`) são rejeitados.

Cada operação válida grava uma movimentação (tipo, quantidade, saldo após, data UTC) na mesma transação do saldo.

### `POST /materiais/{id}/entrada`

Soma a quantidade ao saldo: `saldo atual = saldo anterior + quantidade`.

| Resposta | Descrição |
|---|---|
| `200` | o material com o novo saldo e o status atualizado (uma entrada em material zerado volta a `"Disponível"`) |
| `404` | `"O material 99 não existe."` |
| `422` | quantidade inválida (ver abaixo) |

### `POST /materiais/{id}/saida`

Subtrai a quantidade do saldo: `saldo atual = saldo anterior − quantidade`. É **bloqueada** se a quantidade for maior que o saldo. Saída igual ao saldo é permitida e leva o material a `"Indisponível"`.

| Resposta | Descrição |
|---|---|
| `200` | o material com o novo saldo e o status atualizado |
| `404` | `"O material 99 não existe."` |
| `409` | `"Saldo insuficiente de 'Resma A4': disponível 5, solicitado 8."` (saldo e movimentações ficam inalterados) |
| `422` | quantidade inválida (ver abaixo) |

### Erros `422` de quantidade (entrada e saída)

| Situação | Mensagem |
|---|---|
| ausente | `"O campo 'quantidade' é obrigatório."` |
| 0 ou negativa | `"A quantidade deve ser um número inteiro maior que zero."` |
| decimal ou texto | `"O campo 'quantidade' deve ser um número inteiro."` |
| JSON malformado | `"O corpo da requisição não é um JSON válido."` |

---

## Usuários

**Permissão** de todas as rotas desta seção: `gerir_usuarios` (perfil administrador).

### `GET /usuarios`

Lista todos os usuários (ativos e inativos) em ordem alfabética de nome.

### `GET /usuarios/{id}`

| Resposta | Descrição |
|---|---|
| `200` | o usuário |
| `404` | `"O usuário 99 não existe."` |

### `POST /usuarios`

Cadastra um usuário.

| Campo | Tipo | Obrigatório | Regra |
|---|---|---|---|
| `nome` | texto | sim | não vazio |
| `cpf` | texto | sim | 11 dígitos com dígitos verificadores válidos; aceita máscara; **único** |
| `email` | texto | sim | formato `nome@dominio.ext`; guardado em minúsculas; não é único |
| `perfil` | texto | sim | `administrador`, `estoquista` ou `operador` |
| `senha` | texto | não (padrão `123456`) | mínimo de 6 caracteres; se omitida, vale a senha padrão do protótipo |

```json
{
  "nome": "Maria Silva",
  "cpf": "529.982.247-25",
  "email": "maria@exemplo.com",
  "perfil": "estoquista",
  "senha": "senha-segura-1"
}
```

| Resposta | Descrição |
|---|---|
| `201` | o usuário criado (CPF só com dígitos, sem senha) |
| `409` | `"Já existe um usuário com o CPF 529.982.247-25."` (vale também para usuário inativo e para CPF com máscara diferente) |
| `422` | `"CPF inválido."` |
| `422` | `"O nome do usuário é obrigatório."` |
| `422` | `"O e-mail informado é inválido."` |
| `422` | `"Perfil inválido. Use administrador, estoquista ou operador."` |
| `422` | `"A senha deve ter pelo menos 6 caracteres."` |

### `PUT /usuarios/{id}`

Atualiza nome, e-mail, perfil e, opcionalmente, a senha. **O CPF não pode ser alterado.**

```json
{ "nome": "Maria Souza", "email": "maria.souza@exemplo.com", "perfil": "operador", "senha": null }
```

`senha` ausente ou `null` mantém a senha atual.

| Resposta | Descrição |
|---|---|
| `200` | o usuário atualizado |
| `404` | usuário inexistente |
| `409` | `"Não é possível inativar ou alterar o perfil do último administrador ativo."` |
| `422` | dados inválidos (mesmas mensagens do cadastro) |

### `POST /usuarios/{id}/inativar`

Inativa o usuário: ele deixa de entrar e perde o acesso na hora. Nada é apagado.

| Resposta | Descrição |
|---|---|
| `200` | o usuário, com `"ativo": false` |
| `404` | usuário inexistente |
| `409` | último administrador ativo |

### `POST /usuarios/{id}/reativar`

Devolve o acesso ao usuário. Respostas: `200` com `"ativo": true`, ou `404`.

---

## Exemplo de ponta a ponta

Os clientes precisam guardar e reenviar o cookie de sessão (`-c` grava e `-b` envia, no `curl`):

```bash
# entra como estoquista (o cookie fica em cookies.txt)
curl -c cookies.txt -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"cpf": "529.982.247-25", "senha": "senha-segura-1"}'

# cria o material (categoria 1 = Papelaria)
curl -b cookies.txt -X POST http://localhost:8000/materiais \
  -H "Content-Type: application/json" \
  -d '{"nome": "Resma A4", "categoria_id": 1, "quantidade": 5}'

# entrada de 3 (403 para o estoquista; precisa do perfil operador)
curl -b cookies.txt -X POST http://localhost:8000/materiais/1/entrada \
  -H "Content-Type: application/json" -d '{"quantidade": 3}'

# pesquisa por nome e status
curl -b cookies.txt "http://localhost:8000/materiais?q=resma&status=Dispon%C3%ADvel"

# sai
curl -b cookies.txt -X POST http://localhost:8000/logout
```

Para testar entrada e saída, entre como **operador**. No PowerShell, use `curl.exe` e escape as aspas do JSON, ou envie por `Invoke-RestMethod -SessionVariable`.
