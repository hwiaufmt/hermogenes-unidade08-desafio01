# Guia de uso

Como usar o **Controle de Materiais de Escritório** pelo navegador. Para instalar e iniciar o app, veja o [README](../README.md). Para entender o produto como um todo (para quem serve, escopo e riscos), veja a [visão do produto](visao-do-produto.md).

Com o app rodando, abra <http://localhost:8000>. Você precisa **entrar com CPF e senha**. O que aparece na barra do topo depende do seu **perfil**.

## Perfis

| Perfil | O que faz | Telas |
|---|---|---|
| **Estoquista** | cadastra materiais (com estoque inicial e mínimo), cria e edita categorias e consulta o estoque e os saldos | Pesquisa, Saldos, Cadastro |
| **Operador** | registra entradas e saídas e consulta o estoque e os saldos | Pesquisa, Saldos, Movimentar |
| **Administrador** | mantém os usuários (e só isso) | Usuários |

Cada pessoa tem um único perfil. Se você tentar abrir uma tela que o seu perfil não permite, aparece "Acesso negado" com um link para a sua tela inicial.

## Entrar e sair

1. Abra o endereço do sistema. Sem login, você é levado à tela **Entrar**.
2. Digite o **CPF** (com ou sem pontos e traço) e a **senha**, e clique em **Entrar**.
3. Você cai na primeira tela do seu perfil. Seu nome e perfil aparecem no canto superior direito.
4. Para sair, clique em **Sair**.

Se o CPF ou a senha estiverem errados, aparece "CPF ou senha inválidos.". A mensagem é a mesma para CPF inexistente, senha errada e usuário inativo, de propósito. A sessão dura 8 horas; depois disso, ou se o seu acesso for desativado, o sistema leva você de volta ao login.

### Primeiro acesso (quem instala o sistema)

Em um banco sem usuários, o sistema cria sozinho o **administrador padrão do protótipo**: CPF `529.982.247-25` e senha `123456`. Entre com ele e cadastre os demais usuários. Para usar outro CPF e senha, quem inicia o sistema define `ESTOQUE_ADMIN_CPF` e `ESTOQUE_ADMIN_SENHA` (veja o [README](../README.md#primeiro-acesso)).

Quem for cadastrado sem senha informada também fica com a senha padrão `123456`; peça que troque (hoje a troca é feita por um administrador, editando o usuário).

## Fluxo básico

1. **Administrador:** cadastra os usuários (estoquistas e operadores).
2. **Estoquista:** cadastra categorias e materiais, informando estoque inicial e mínimo.
3. **Operador:** registra entradas (reposição) e saídas (retiradas).
4. **Estoquista e operador:** procuram materiais na **Pesquisa** e conferem os totais na tela **Saldos**.

## Tela Usuários (`/gestao/usuarios`, administrador)

### Novo usuário

| Campo | Descrição |
|---|---|
| Nome | obrigatório |
| CPF | obrigatório, com dígitos verificadores válidos; aceita pontos e traço. **Não pode se repetir** |
| E-mail | obrigatório, no formato `nome@dominio.com` |
| Perfil | administrador, estoquista ou operador |
| Senha | opcional: em branco, vale a senha padrão `123456`. Se informada, mínimo de 6 caracteres |

Clique em **Cadastrar usuário**. Se o CPF já existe, o sistema recusa com "Já existe um usuário com o CPF ...", mesmo que o usuário esteja inativo.

### Lista de usuários

A tabela mostra nome, CPF, e-mail, perfil e situação (Ativo ou Inativo), com as ações:

- **Editar:** o formulário passa a editar aquele usuário. Nome, e-mail e perfil podem mudar; o **CPF fica travado**. Deixe a senha em branco para mantê-la, ou digite uma nova. Clique em **Cancelar edição** para voltar ao cadastro.
- **Inativar:** o usuário deixa de entrar e perde o acesso na hora, mesmo logado. Nada é apagado.
- **Reativar:** devolve o acesso.

O **último administrador ativo** não pode ser inativado nem ter o perfil trocado: o sistema mostra "Não é possível inativar ou alterar o perfil do último administrador ativo.". Cadastre outro administrador antes.

> Mudanças de perfil e inativações valem a partir da próxima ação da pessoa afetada.

## Tela Cadastro (`/materiais/novo`, estoquista)

### Novo material

| Campo | Descrição |
|---|---|
| Nome | obrigatório |
| Categoria | obrigatória; escolha uma da lista |
| Estoque inicial | inteiro a partir de 0 (padrão 0). Com 0, o material nasce **Indisponível** |
| Estoque mínimo | inteiro a partir de 0 (padrão 0). É guardado e exibido, mas **não gera alerta** |

Clique em **Cadastrar material**. Uma mensagem confirma o cadastro, ou explica o problema (por exemplo, "Selecione uma categoria.").

### Nova categoria

Se a categoria que você precisa não existe, digite o nome em **Nova categoria** e clique em **Criar categoria**. Ela aparece na lista de categorias do formulário de material, já selecionada. Nomes repetidos são recusados **sem diferenciar maiúsculas de minúsculas**: se já existe "Escrita", não dá para criar "escrita" nem "ESCRITA". As categorias iniciais são Papelaria, Escrita e Informática.

### Editar categoria

Mais abaixo na página, a seção **Categorias cadastradas** lista cada categoria com **quantos materiais ela tem** e um botão **Editar**.

1. Clique em **Editar** na linha da categoria. Abre uma janela com o nome atual selecionado.
2. Digite o novo nome e clique em **Salvar alteração** (ou tecle Enter). **Cancelar**, ou a tecla Esc, fecha a janela sem mudar nada.
3. **Se a categoria não tem materiais**, o nome é gravado na hora.
4. **Se a categoria tem materiais**, o sistema **não grava ainda** e abre uma janela de confirmação, por exemplo: *"Esta categoria tem 3 materiais; a mudança de nome afetará 3 registros. Confirme para gravar."* Escolha:
   - **Confirmar alteração:** grava. Uma mensagem informa o novo nome e quantos registros foram afetados, e os materiais passam a aparecer na categoria com o novo nome.
   - **Voltar:** reabre a edição, com o nome que você digitou, para ajustar ou desistir.

Se o novo nome já existir (em qualquer caixa, "papelaria" conta como "Papelaria"), o erro aparece na própria janela de edição e **nenhuma confirmação é pedida**. Trocar só maiúsculas e minúsculas do próprio nome ("Limpeza" para "LIMPEZA") é permitido e segue as mesmas regras acima.

> Excluir categorias e editar ou excluir materiais não faz parte do MVP. Os valores de estoque (inicial e mínimo) são informados no cadastro.

## Tela Movimentar (`/movimentar`, operador)

1. Escolha o **Material**. O painel **Saldo atual** mostra o saldo e o status.
2. Escolha o **Tipo**: **Entrada** (soma ao saldo) ou **Saída** (subtrai do saldo).
3. Informe a **Quantidade**, um inteiro maior que zero.
4. Clique em **Registrar**.

Depois do registro, a mensagem informa o novo saldo e o painel é atualizado.

**Saída maior que o saldo é bloqueada.** O sistema mostra, por exemplo, "Saldo insuficiente de 'Caneta azul': disponível 5, solicitado 8.". O saldo não muda e nada é registrado.

Quando o saldo chega a 0, o status passa a **Indisponível** automaticamente. Uma nova entrada o devolve a **Disponível**, sem ação manual.

## Tela Pesquisa (`/pesquisa`, estoquista e operador)

Mostra os materiais **agrupados por categoria**, em ordem alfabética, com saldo, estoque mínimo e status. Os filtros se combinam:

- **Buscar por nome:** digite parte do nome; a lista se atualiza sozinha. Maiúsculas e minúsculas não importam (para letras acentuadas, prefira digitar como está cadastrado).
- **Categoria:** "Todas as categorias" ou uma só.
- **Status:** Todos, Disponível ou Indisponível.

Abaixo dos filtros, um resumo diz quantos materiais foram encontrados. Se nada atende aos filtros, aparece "Nenhum material encontrado com esses filtros."; se não há material cadastrado, "Nenhum material cadastrado.".

Materiais **Indisponíveis** ficam destacados: linha com fundo avermelhado e selo "⚠ Indisponível". Os demais mostram "✓ Disponível". Em telas estreitas, a tabela rola na horizontal e pode ser percorrida pelo teclado.

## Tela Saldos (`/estoque/saldos`, estoquista e operador)

Mostra os **totais do estoque**, em três blocos. Não há filtros: para procurar um material, use a Pesquisa.

1. **Total geral:** três cartões com quantos **materiais** existem, quantas **unidades** há em estoque (a soma dos saldos) e quantos materiais estão **indisponíveis** (saldo 0). O número de indisponíveis fica em vermelho quando é maior que zero.
2. **Resumo por categoria:** uma linha por categoria, com materiais, unidades e indisponíveis. **Categorias sem material também aparecem**, com zeros (por exemplo, "Informática: 0, 0, 0").
3. **Saldo por material:** um quadro por categoria que tem material, com cada material, seu saldo, o estoque mínimo e o status. Materiais **Indisponíveis** ficam destacados, como na Pesquisa.

Os números são calculados pelo sistema e refletem as entradas e saídas já registradas, mas a tela **não se atualiza sozinha**: clique em **Atualizar saldos** (no alto da página) para buscar os valores mais recentes, por exemplo depois que alguém registrou uma saída. Em telas estreitas, as tabelas rolam na horizontal e podem ser percorridas pelo teclado.

## Mensagens de erro

Os erros aparecem em uma faixa no topo da tela, em português. As mais comuns:

| Mensagem | O que fazer |
|---|---|
| CPF ou senha inválidos. | conferir o CPF e a senha; se o acesso foi desativado, falar com um administrador |
| É necessário entrar no sistema. | entrar de novo (a sessão caiu) |
| Você não tem permissão para realizar esta ação. | usar uma tela do seu perfil, ou pedir a mudança de perfil a um administrador |
| Selecione uma categoria. | escolher uma categoria no formulário de material |
| O nome do material é obrigatório. | preencher o nome |
| O campo 'quantidade' deve ser um número inteiro. | usar um número inteiro, sem vírgula |
| A quantidade deve ser um número inteiro maior que zero. | usar 1 ou mais |
| Saldo insuficiente de '...': disponível N, solicitado M. | pedir no máximo o saldo disponível, ou registrar uma entrada antes |
| Já existe uma categoria chamada '...'. | usar a categoria existente (a mensagem mostra o nome já cadastrado, mesmo que você tenha digitado em outra caixa) |
| Esta categoria tem N materiais; a mudança de nome afetará N registros. Confirme para gravar. | não é um erro: é o aviso antes de gravar. Use **Confirmar alteração** para seguir ou **Voltar** para desistir |
| CPF inválido. | conferir os 11 dígitos |
| Já existe um usuário com o CPF .... | o usuário já está cadastrado (talvez inativo; reative-o) |
| A senha deve ter pelo menos 6 caracteres. | escolher uma senha maior (ou deixar em branco para usar a padrão) |
| O e-mail informado é inválido. | usar o formato `nome@dominio.com` |

## Perguntas frequentes

**Onde ficam os dados?** No arquivo `estoque.db`, na pasta do projeto. Para recomeçar do zero, pare o app e apague esse arquivo; as três categorias iniciais voltam na próxima execução, e o administrador padrão (ou o definido por `ESTOQUE_ADMIN_CPF` e `ESTOQUE_ADMIN_SENHA`) é recriado.

**Esqueci minha senha.** Ainda não há recuperação de senha pelo próprio usuário. Um administrador pode definir uma nova senha editando o seu cadastro na tela Usuários.

**Esqueci a senha do único administrador.** O administrador padrão só é criado em um banco sem usuários, então não ajuda se já existem usuários. Nesse caso é preciso intervir no banco ou recriá-lo (perdendo os dados). Por isso, mantenha pelo menos dois administradores.

**Posso ver o histórico de entradas e saídas, ou quem fez cada uma?** Não na interface. Cada movimentação é gravada no banco (tipo, quantidade, saldo após e data UTC), mas o histórico em tela e o registro de **quem** movimentou estão fora do escopo por ora.

**O estoque mínimo avisa quando o saldo está baixo?** Não. No MVP ele só é guardado e exibido.

**Posso apagar um usuário?** Não. Use **Inativar**, que preserva o registro.
