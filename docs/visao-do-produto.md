# Visão do produto: Controle de Materiais de Escritório

| | |
|---|---|
| **Produto** | Controle de Materiais de Escritório |
| **Estado** | Protótipo funcional (as seis sprints de funcionalidades estão concluídas) |
| **Público deste documento** | Equipe e donos do produto |
| **Data** | 29/10/2026 |

Este documento descreve **o que o produto é, para quem serve e o que ele faz hoje**. Ele não é um plano de futuro: onde falta uma informação que só o dono do produto tem (metas, números do negócio), o texto diz **"a definir"** em vez de inventar. Para o uso das telas, veja o [guia de uso](guia-de-uso.md); para a API, a [referência da API](api.md); para o desenho técnico, a [arquitetura](arquitetura.md).

---

## 1. Resumo

O **Controle de Materiais de Escritório** é uma aplicação web para saber, a qualquer momento, **quanto há de cada material de escritório** (papelaria, escrita, informática e o que mais a organização queira acompanhar). As pessoas cadastram os materiais por categoria, registram **entradas** (reposição) e **saídas** (retiradas) e consultam o **saldo atualizado**.

O produto nasceu como um **MVP** com um objetivo único: validar o ciclo *cadastrar → registrar entrada → registrar saída → consultar saldo* com **regras de negócio confiáveis**. Sobre esse ciclo foram acrescentados, por decisão do dono do produto, o **controle de acesso** (usuários, login e três perfis) e duas melhorias de uso (edição de categorias com aviso de impacto e uma visão de saldos).

Hoje o sistema roda em um único computador, com um arquivo de banco de dados, e é um **protótipo**: funciona de ponta a ponta, mas algumas escolhas de segurança foram simplificadas de propósito e **não servem para uso real** (ver seção 10).

## 2. Problema e oportunidade

Em muitos escritórios, o estoque de materiais é controlado de maneira informal: uma planilha, um caderno, a memória de quem cuida do armário. Isso costuma gerar três problemas:

| Problema | Consequência |
|---|---|
| **Falta de itens** | Alguém precisa de um material e descobre, na hora, que acabou |
| **Compras duplicadas** | Compra-se o que já existe, porque ninguém sabe o saldo real |
| **Falta de visibilidade** | Não há um lugar único onde ver o que existe, o que está zerado e quanto há de cada coisa |

A oportunidade é oferecer **um único lugar confiável** para o saldo de cada material: um saldo que só muda por movimentações registradas, que **nunca fica negativo** e que qualquer pessoa autorizada consegue consultar sem depender de quem "sabe de cabeça".

## 3. Usuários e perfis

O sistema é usado por pessoas cadastradas (nome, CPF e e-mail), que entram com **CPF e senha**. Cada pessoa tem **um** de três perfis, e cada perfil enxerga e faz **somente** o que lhe cabe, tanto nas telas quanto na API.

| Perfil | Quem é | O que faz no sistema |
|---|---|---|
| **Estoquista** | Quem cuida do cadastro e da organização do estoque | Cadastra materiais (informando estoque inicial e mínimo), cria e edita categorias e consulta o estoque e os saldos |
| **Operador** | Quem retira e repõe o material no dia a dia | Registra entradas e saídas e consulta o estoque e os saldos |
| **Administrador** | Quem mantém o acesso ao sistema | Cadastra, edita, inativa e reativa usuários. **Não** mexe no estoque |

| Ação | Estoquista | Operador | Administrador |
|---|:---:|:---:|:---:|
| Criar categoria | ✅ | | |
| Editar categoria (com aviso de impacto) | ✅ | | |
| Cadastrar material | ✅ | | |
| Consultar o estoque (Pesquisa e Saldos) | ✅ | ✅ | |
| Registrar entrada e saída | | ✅ | |
| Manter usuários | | | ✅ |

Duas decisões de produto explicam essa divisão: quem cadastra o estoque **não** é quem o movimenta (o estoquista não registra entradas nem saídas), e quem administra os acessos **não** vê nem altera o estoque. Perfis e permissões vivem em um único lugar do sistema, e as telas, o menu e a API leem a mesma regra.

## 4. Objetivos e proposta de valor

### Objetivos

1. **Validar o ciclo** cadastrar → entrada → saída → consultar saldo, com regras que garantam que o saldo é confiável.
2. Dar **visibilidade** do que existe, do que acabou e de quanto há por categoria.
3. Controlar **quem pode fazer o quê**, sem depender de combinados informais.

### Valor por perfil

| Perfil | O que ganha |
|---|---|
| **Operador** | Registrar uma retirada ou reposição em poucos passos, com resposta imediata do novo saldo e um aviso claro quando o saldo não basta |
| **Estoquista** | Manter o cadastro organizado por categoria e ter uma visão consolidada do que há e do que está zerado |
| **Administrador** | Decidir quem entra no sistema e com que papel, e retirar o acesso de alguém na hora, sem apagar o cadastro dessa pessoa |

Quem consulta os saldos (estoquista ou operador) ganha o mesmo: ver o saldo real **antes de comprar ou pedir**, o que ajuda a evitar compras duplicadas e faltas. O sistema não tem um perfil específico para quem decide compras.

## 5. Escopo atual

O que o produto **faz hoje**, por capacidade.

### Categorias
- Três categorias iniciais: **Papelaria**, **Escrita** e **Informática**.
- O estoquista cria novas categorias e **edita o nome** de uma categoria.
- O nome é único **sem diferenciar maiúsculas de minúsculas**: "Escrita" e "escrita" são a mesma categoria.
- Ao editar uma categoria que **já tem materiais**, o sistema **informa quantos registros serão afetados** e só grava depois de uma confirmação. Se a categoria não tem materiais, grava direto.

### Materiais
- Todo material pertence a **uma categoria válida**; sem categoria, o sistema não grava.
- No cadastro, informa-se o **estoque inicial** e o **estoque mínimo** (ambos opcionais, padrão 0).
- O **status** é automático: **Indisponível** quando o saldo é 0 e **Disponível** nos demais casos. Não há campo para alterá-lo à mão.
- O estoque mínimo é **guardado e exibido**, mas **não gera alerta**.

### Movimentação
- A **entrada** soma ao saldo e a **saída** subtrai.
- Uma saída maior que o saldo é **bloqueada**: o saldo fica como está, nada é registrado e a tela explica o motivo.
- Cada entrada e saída **grava um registro** (tipo, quantidade, saldo depois da operação e data), e o saldo e o registro são gravados **juntos ou não são gravados**.

### Consulta
- **Pesquisa:** lista os materiais agrupados por categoria, com **busca por nome** e filtros de **categoria** e **status**.
- **Saldos:** mostra o **total geral** (materiais, unidades e indisponíveis), o **resumo por categoria** (inclusive categorias sem material) e o **saldo de cada material**. Os números são calculados pelo sistema.
- Materiais **indisponíveis** ficam destacados nas duas telas, com texto e ícone, não só com cor.

### Usuários e acesso
- Cadastro de usuários com **CPF único**: não se aceita CPF repetido, nem com máscara diferente, nem de um usuário inativo; o CPF precisa ter dígitos verificadores válidos.
- **Login** por CPF e senha, com sessão de 8 horas. A resposta é a mesma para CPF inexistente, senha errada e usuário inativo, para não revelar quais CPFs existem.
- Usuários **não são apagados, apenas inativados**; um usuário inativado perde o acesso na hora, mesmo logado.
- O **último administrador ativo** não pode ser inativado nem rebaixado, para o sistema nunca ficar sem quem o administre.

### Qualidade de uso
- Funciona em **computador e celular**.
- Acessibilidade básica: campos com rótulo, foco visível, mensagens anunciadas a leitores de tela, alvos de toque de 44 px e contraste conferido.
- As **mensagens das telas e os erros das operações** do sistema (saldo insuficiente, CPF inválido, nome repetido e outros) estão em português. A exceção são as respostas padrão do framework para **endereços inexistentes** e **métodos não permitidos**, que saem em inglês ("Not Found", "Method Not Allowed"), e a documentação interativa da API (`/docs`).
- Testes automatizados cobrem **todos os critérios de aceite** (CA-01 a CA-11).

## 6. Fora do escopo

O que o produto **não faz**, de propósito:

| Área | O que não existe hoje |
|---|---|
| **Processos de compra** | Aprovação de requisições, fornecedores, notas fiscais |
| **Análise e relatórios** | Relatórios, painéis analíticos (*dashboards*) e exportação de dados. A tela Saldos é uma **consulta** do estado atual, não um relatório: não há gráficos, períodos nem comparações |
| **Histórico** | Tela de histórico de movimentações, extrato por material, saldo em data passada, edição ou exclusão de movimentações |
| **Alertas e integrações** | Alerta de estoque baixo (o mínimo só é exibido), notificações, integração com outros sistemas (ERP, e-mail) |
| **Organização** | Várias filiais ou locais de estoque |
| **Cadastro** | Exclusão de categorias; edição de um material já cadastrado (os valores de estoque são informados no cadastro) |
| **Contas** | Troca ou recuperação de senha pelo próprio usuário, limite de tentativas de login, login por provedor externo, edição de CPF, exclusão definitiva de usuários |
| **Autoria** | Registro de **quem** fez cada movimentação |
| **Plataformas** | Aplicativo nativo para celular (a interface web funciona no celular) |

## 7. Evolução do produto

O escopo original era apenas o ciclo de estoque. Três sprints o entregaram; as seguintes ampliaram o produto **a pedido do dono do produto**.

| Sprint | O que o produto ganhou | Origem |
|---|---|---|
| **1. Fundação e cadastro** | Categorias iniciais, cadastro de materiais por categoria e listagem | Escopo original |
| **2. Entrada e saída** | Registro de movimentações, bloqueio por saldo insuficiente e status automático "Indisponível" | Escopo original |
| **3. Consulta e acabamento** | Estoque agrupado por categoria com filtro, destaque visual do indisponível, interface responsiva e acessível, documentação inicial | Escopo original |
| **4. Usuários, login e permissões** | Usuários com CPF único, login, três perfis, telas e menu por perfil, e a Pesquisa com busca e filtros | Pedido do dono |
| **5. Edição de categoria** | Edição do nome da categoria, com aviso de quantos registros serão afetados e confirmação; nome sem diferenciar maiúsculas | Pedido do dono |
| **6. Consulta de saldos** | A visão Saldos, com total geral, resumo por categoria e saldo por material | Pedido do dono |
| **7. Documento de visão** | Este documento | Pedido do dono |

Cada sprint foi entregue em partes pequenas, verificada contra os critérios de aceite e documentada.

## 8. Princípios do produto

Regras que valem em todo o produto e orientam qualquer decisão:

1. **O saldo é confiável.** Ele só muda por entrada ou saída registrada, **nunca fica negativo**, e a verificação de saldo e a subtração acontecem como **uma só operação**, para duas retiradas simultâneas não consumirem o mesmo saldo.
2. **Tudo ou nada.** Uma operação ou é gravada por inteiro, ou não é gravada.
3. **As regras vivem no servidor.** A interface só mostra e pede; ela não calcula saldo, status nem totais.
4. **Cada perfil só faz o que lhe cabe**, e isso vale na API e nas telas, não apenas por esconder botões.
5. **Nada é apagado sem necessidade.** Usuários são inativados, e o histórico de movimentações é preservado.
6. **Avisar antes de afetar.** Uma mudança que atinge registros existentes informa quantos serão afetados antes de ser gravada. **Hoje isso vale para a edição de categoria**; é o único ponto do sistema em que uma alteração atinge outros registros.
7. **Falar a língua de quem usa.** Mensagens claras, em português, que dizem o que aconteceu e o que fazer.
8. **Acessível e responsivo.** Utilizável em computador e celular, por quem usa teclado e por quem usa leitor de tela.

## 9. Métricas de sucesso

> **Todas as métricas abaixo são hipóteses a validar com o dono do produto.** Nenhuma meta numérica foi definida: o campo "meta" está **a definir** em todas.

| Métrica | O que mostra | Como medir | Meta |
|---|---|---|---|
| **Acurácia do saldo** | Se o saldo no sistema corresponde ao que existe de fato | Contar fisicamente uma amostra de materiais e comparar com o saldo do sistema | A definir |
| **Rupturas inesperadas** | Quantas vezes alguém precisou de um item que estava zerado sem que isso fosse sabido | Contar os pedidos não atendidos por falta de material, comparando com o status "Indisponível" | A definir |
| **Compras duplicadas** | Se a visibilidade do saldo evita comprar o que já existe | Registrar compras de itens que ainda tinham saldo no sistema | A definir |
| **Adoção** | Se o sistema é usado como fonte única | Comparar a quantidade de retiradas reais com a de saídas registradas | A definir |
| **Tempo para registrar uma movimentação** | Se registrar é rápido o bastante para ser feito sempre | Cronometrar o fluxo de uma entrada ou saída, do login à confirmação | A definir |

Duas garantias, ao contrário, **já são verificáveis no próprio sistema**: **nenhum saldo negativo** e **nenhum CPF repetido**, ambos impedidos pelas regras e cobertos por testes automatizados.

**Limite de medição:** as movimentações ficam gravadas no banco (tipo, quantidade, saldo depois e data), mas **não há tela de histórico** e o registro **não diz quem fez** cada uma. Por isso, parte das métricas acima depende de contagem manual ou de consulta direta ao banco.

## 10. Premissas, restrições e riscos

Esta seção descreve **o estado atual**: o que se assume, o que limita o produto hoje e o que pode dar errado.

### Premissas
- Existe **um único estoque** (um local), com os materiais contados em **unidades inteiras**.
- O saldo reflete a realidade **desde que as movimentações sejam registradas**: o sistema não sabe de retiradas que ninguém lançou.
- Quem usa o sistema tem **login** e recebe **um perfil**.
- As categorias são poucas e conhecidas; não há exclusão de categorias.

### Restrições técnicas
- O banco é **um arquivo local** (SQLite) e **não há migração**: mudar a estrutura de uma tabela existente exige recriar o banco ou alterá-lo à mão.
- Um material já cadastrado **não pode ser editado**; só o seu saldo muda, por movimentação.
- A movimentação **não registra o autor**, e **não há histórico em tela**.
- O estoque mínimo é só informativo: **não há alerta de estoque baixo**.
- A comparação de maiúsculas e minúsculas na busca por nome é garantida para letras sem acento; letras acentuadas podem não casar entre maiúscula e minúscula.
- Endereços inexistentes e métodos não permitidos respondem com a mensagem padrão do framework, em inglês.

### Riscos e limitações do protótipo

| Risco | Situação hoje | Efeito |
|---|---|---|
| **Segurança de senhas simplificada** | A senha mínima é de 6 caracteres, existe uma **senha padrão (`123456`)** para quem é cadastrado sem senha, e **não há limite de tentativas** de login | Quem descobrir o CPF de um usuário que ficou com a senha padrão entra com ela |
| **Administrador padrão no código** | Em um banco sem usuários, o sistema cria um administrador com CPF e senha conhecidos, definidos no próprio código | Quem conhece o projeto sabe esse acesso |
| **Chave da sessão** | Sem configuração, uma chave aleatória é gerada a cada início do sistema | Todos são desconectados quando o sistema reinicia |
| **Cookie sem proteção de HTTPS** | O cookie de sessão funciona em conexão comum (sem a marca "seguro") | Adequado para uso local, não para a internet |
| **Dependência de um único administrador** | Não há recuperação de senha pelo usuário | Se o único administrador perde a senha, é preciso intervir no banco |
| **Falta de autoria** | Não se sabe quem fez cada movimentação | Dificulta apurar divergências de saldo |
| **Banco em um arquivo** | Atende bem a um escritório pequeno em um computador | Não foi desenhado para muitos usuários simultâneos nem para vários locais |

**Em resumo: o produto cumpre o seu propósito de validar o ciclo de estoque e o controle de acesso, mas, como está, é um protótipo para uso controlado, e não um sistema pronto para uso real.**
