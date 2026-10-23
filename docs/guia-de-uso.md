# Guia de uso

Como usar o **Controle de Materiais de Escritório** pelo navegador. Para instalar e iniciar o app, veja o [README](../README.md).

Com o app rodando, abra <http://localhost:8000>. A barra do topo leva às três telas: **Estoque**, **Movimentar** e **Cadastro**.

## Fluxo básico

1. **Cadastro:** cadastre o material em uma categoria.
2. **Movimentar:** registre entradas (reposição) e saídas (retiradas).
3. **Estoque:** consulte os saldos por categoria.

## Tela Cadastro (`/materiais/novo`)

### Novo material

| Campo | Descrição |
|---|---|
| Nome | obrigatório |
| Categoria | obrigatória; escolha uma da lista |
| Estoque inicial | inteiro a partir de 0 (padrão 0). Com 0, o material nasce **Indisponível** |
| Estoque mínimo | inteiro a partir de 0 (padrão 0). É guardado e exibido, mas **não gera alerta** |

Clique em **Cadastrar material**. Uma mensagem confirma o cadastro, ou explica o problema (por exemplo, "Selecione uma categoria.").

### Nova categoria

Se a categoria que você precisa não existe, digite o nome em **Nova categoria** e clique em **Criar categoria**. Ela aparece na lista de categorias do formulário de material, já selecionada. Nomes repetidos são recusados. As categorias iniciais são Papelaria, Escrita e Informática.

> Editar ou excluir categorias e materiais não faz parte do MVP.

## Tela Movimentar (`/movimentar`)

1. Escolha o **Material**. O painel **Saldo atual** mostra o saldo e o status.
2. Escolha o **Tipo**: **Entrada** (soma ao saldo) ou **Saída** (subtrai do saldo).
3. Informe a **Quantidade**, um inteiro maior que zero.
4. Clique em **Registrar**.

Depois do registro, a mensagem informa o novo saldo e o painel é atualizado.

**Saída maior que o saldo é bloqueada.** O sistema mostra, por exemplo, "Saldo insuficiente de 'Caneta azul': disponível 5, solicitado 8.". O saldo não muda e nada é registrado.

Quando o saldo chega a 0, o status passa a **Indisponível** automaticamente. Uma nova entrada o devolve a **Disponível**, sem ação manual.

## Tela Estoque (`/`)

Mostra os materiais **agrupados por categoria**, em ordem alfabética, com saldo, estoque mínimo e status.

- Use o filtro **Categoria** para ver só uma categoria. "Todas as categorias" mostra todas que têm material.
- Se a categoria escolhida não tem itens, aparece "Nenhum material nesta categoria.".
- Materiais **Indisponíveis** ficam destacados: linha com fundo avermelhado e selo "⚠ Indisponível". Os demais mostram "✓ Disponível".
- Em telas estreitas, a tabela rola na horizontal; ela pode ser percorrida pelo teclado.

## Mensagens de erro

Os erros aparecem em uma faixa no topo da tela, em português. As mais comuns:

| Mensagem | O que fazer |
|---|---|
| Selecione uma categoria. | escolher uma categoria no formulário de material |
| O nome do material é obrigatório. | preencher o nome |
| O campo 'quantidade' deve ser um número inteiro. | usar um número inteiro, sem vírgula |
| A quantidade deve ser um número inteiro maior que zero. | usar 1 ou mais |
| Saldo insuficiente de '...': disponível N, solicitado M. | pedir no máximo o saldo disponível, ou registrar uma entrada antes |
| Já existe uma categoria chamada '...'. | usar a categoria existente |

## Perguntas frequentes

**Onde ficam os dados?** No arquivo `estoque.db`, na pasta do projeto. Para recomeçar do zero, pare o app e apague esse arquivo; as três categorias iniciais voltam na próxima execução.

**Posso ver o histórico de entradas e saídas?** Não na interface. Cada movimentação é gravada no banco (tipo, quantidade, saldo após e data UTC), mas o histórico em tela está fora do escopo do MVP.

**O estoque mínimo avisa quando o saldo está baixo?** Não. No MVP ele só é guardado e exibido.
