# Referência da API

API REST em JSON. Com o app rodando, a documentação interativa (Swagger) fica em <http://localhost:8000/docs>.

## Convenções

- Corpo e respostas em `application/json`.
- Erros devolvem `{"detail": "mensagem em português"}`. O `detail` é sempre **texto**, inclusive nos `422` de validação.
- Quando há mais de um problema de validação, as mensagens vêm unidas num só texto.

### Códigos de erro

| Código | Quando |
|---|---|
| `404` | material ou categoria inexistente |
| `409` | saldo insuficiente para a saída |
| `422` | dado inválido: campo ausente, tipo errado, valor fora do limite, categoria inválida, nome duplicado |

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

`status` é calculado pelo servidor: `"Indisponível"` quando `quantidade` é 0, senão `"Disponível"`.

---

## Categorias

### `GET /categorias`

Lista as categorias em ordem alfabética. Já vem com Papelaria, Escrita e Informática.

**200**

```json
[
  { "id": 2, "nome": "Escrita" },
  { "id": 3, "nome": "Informática" },
  { "id": 1, "nome": "Papelaria" }
]
```

### `POST /categorias`

Cria uma categoria.

**Corpo**

```json
{ "nome": "Limpeza" }
```

O nome é aparado (espaços nas pontas são removidos). Deve ser único.

| Resposta | Descrição |
|---|---|
| `201` | a categoria criada |
| `422` | `"O nome da categoria é obrigatório."` (vazio ou só espaços) |
| `422` | `"Já existe uma categoria chamada 'Limpeza'."` |

---

## Materiais

### `GET /materiais`

Lista os materiais em ordem alfabética de nome.

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `categoria_id` | inteiro, opcional | só os materiais dessa categoria |

| Resposta | Descrição |
|---|---|
| `200` | lista de materiais (vazia se a categoria não tem itens) |
| `404` | `"A categoria 99 não existe."` (filtro com categoria inexistente) |

### `GET /materiais/{id}`

Consulta um material.

| Resposta | Descrição |
|---|---|
| `200` | o material |
| `404` | `"O material 99 não existe."` |

### `POST /materiais`

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

---

## Movimentações

Entrada e saída recebem o mesmo corpo e devolvem o **material atualizado**.

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

## Exemplo de ponta a ponta

```bash
# cria o material (categoria 1 = Papelaria)
curl -X POST http://localhost:8000/materiais \
  -H "Content-Type: application/json" \
  -d '{"nome": "Resma A4", "categoria_id": 1, "quantidade": 5}'

# entrada de 3 (saldo 8)
curl -X POST http://localhost:8000/materiais/1/entrada \
  -H "Content-Type: application/json" -d '{"quantidade": 3}'

# saída de 9 (bloqueada: 409)
curl -X POST http://localhost:8000/materiais/1/saida \
  -H "Content-Type: application/json" -d '{"quantidade": 9}'

# consulta filtrada por categoria
curl "http://localhost:8000/materiais?categoria_id=1"
```

No PowerShell, use `curl.exe` e escape as aspas do JSON, ou envie por `Invoke-RestMethod`.
