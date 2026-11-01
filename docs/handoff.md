# Handoff: Controle de Materiais de Escritório

Para quem assume o projeto (pessoa ou Claude). Estado em **30/10/2026**, `main` em `90cf695`, igual à `origin/main`. Antes de qualquer tarefa, leia o [`CLAUDE.md`](../CLAUDE.md): ele é a fonte de verdade das regras, dos critérios de aceite e das decisões.

## 1. Onde o projeto está

Protótipo funcional, **9 sprints concluídas**, **318 testes passando**, ruff limpo.

| Sprint | Entrega |
|---|---|
| 1 a 3 | Ciclo cadastrar → entrada → saída → consultar saldo; categorias; Pesquisa agrupada; responsividade |
| 4 | Usuários (CPF único), login por CPF + senha, três perfis e matriz de permissões |
| 5 | Edição de categoria com aviso de impacto; nome único sem diferenciar maiúsculas |
| 6 | Tela Saldos |
| 7 | Documento de visão do produto |
| 8 | Exclusão lógica de materiais; tabela de Saldos por material; disponibilidade Sim/Não |
| 9 | Exclusão lógica de categorias |

Critérios de aceite: CA-01 a CA-16 (seção 5 do CLAUDE.md), cada um com testes `test_caNN_*`.

## 2. Como rodar

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload     # http://localhost:8000
pytest
ruff check . ; ruff format .
```

Administrador padrão do protótipo: CPF `529.982.247-25`, senha `123456` (só existe se o banco nasceu sem `ESTOQUE_ADMIN_CPF`/`ESTOQUE_ADMIN_SENHA`).

## 3. Arquitetura em uma frase

Router (HTTP) → service (regra de negócio) → models. Regras só em `app/services/estoque.py` e `usuarios.py`; **quem pode o quê só em `app/permissoes.py`** (API, páginas e menu leem a mesma matriz); o JavaScript só chama a API e renderiza. Detalhes em [`arquitetura.md`](arquitetura.md).

## 4. Decisões que não são óbvias no código

- **Exclusão lógica** de materiais e categorias: coluna `excluido_em`; **todo ponto que lê** filtra os excluídos (`excluido_em IS NULL`). Ao criar uma leitura nova, lembre do filtro. Não há restauração pela interface.
- **Exclusão de categoria:** bloqueada (`409`, com `materiais`) só se algum material ativo tiver **saldo > 0**; os ativos **sem saldo saem junto**, na mesma transação. Essa regra foi corrigida depois da entrega da Sprint 9: a primeira versão bloqueava por qualquer material ativo.
- **Nome de categoria excluída liberado** por um truque: o `UNIQUE` de `categorias.nome` não sai com `ALTER TABLE` no SQLite, então o nome guardado vira `"<nome> [excluída #id]"`.
- **Seed** só cria as 3 categorias iniciais com a tabela **vazia** (contando as excluídas). Um banco com categorias próprias, mas sem as iniciais, não as recebe de volta.
- **Migração leve** (`app/migracoes.py`): só **acrescenta colunas** ao iniciar, idempotente, sem tocar nos dados. Qualquer outra mudança de estrutura exige recriar o banco ou alterar a tabela à mão. Com `--reload`, o servidor migra o `estoque.db` assim que o código é salvo. **Copie `estoque.db` antes de atualizar.**
- **Sim/Não** é só rótulo de tela (`rotuloDisponivel` em `tabelas.js`); a API continua devolvendo `status` `"Disponível"`/`"Indisponível"`.
- **Rotas de página:** `/estoque/saldos` e `/gestao/usuarios` (e não `/saldos` e `/usuarios`), porque estas são a API.
- **Nome da categoria** é comparado por `casefold` no service; acentos diferenciam.

## 5. Armadilhas conhecidas

- **Servidor do dono rodando com `--reload`:** ele mantém o `estoque.db` aberto e migra na hora. Nunca rode testes ou scripts contra esse arquivo. Para verificar no navegador, use um **diretório temporário e outra porta** (`uvicorn --app-dir <projeto>` com `cwd` no diretório temporário) e apague depois pelo PID.
- Uma vez, testes contra o banco real deixaram registros de teste lá (limpos à mão). Os testes atuais usam SQLite em memória.
- **Windows PowerShell 5.1:** `Set-Content -Encoding utf8` grava BOM; mensagem de commit via arquivo deve ser escrita com a ferramenta de arquivos, não com `Set-Content`. `git -F -` não funciona. A ferramenta Bash do ambiente pode travar (alias do Python); prefira PowerShell.
- `git` devolve código de saída 255 por um aviso de TLS desativado, mesmo com commit/push bem-sucedido: confira com `git log`/`git status`.
- `claude.md` e `CLAUDE.md` são o mesmo arquivo no Windows.

## 6. Pendências e decisões em aberto

Do CLAUDE.md, seção 12 (todas **fora do escopo atual**, não implementar sem pedido):

- Registrar **quem** fez cada entrada e saída (`usuario_id` em `Movimentacao`). Seria uma coluna nova, que a migração leve comporta.
- Editar estoque inicial/mínimo de material já cadastrado (hoje só no cadastro).
- Limite de tentativas de login e troca de senha pelo próprio usuário.
- Restaurar material ou categoria excluídos.
- Segurança do protótipo (senha padrão `123456`, administrador no código, chave de sessão): **rever antes de qualquer uso real**.

Observações ainda não tratadas:

- A ordenação dos materiais na Pesquisa é binária (diferencia maiúsculas), diferente de Saldos, que usa `casefold`.
- A tela Saldos não mostra mais categorias sem materiais (a API `/saldos` continua devolvendo-as com zeros).
- Um banco com categorias próprias e sem as iniciais não recebe as iniciais (efeito do seed só com tabela vazia).

## 7. Forma de trabalho combinada com o dono do projeto

Seção 10 do CLAUDE.md, na prática:

1. **Alinhar antes de criar:** para uma mudança nova, listar dúvidas e decisões e perguntar antes de codar.
2. **Uma sprint por pedido**, em **3 partes**: (1) service e API, (2) telas, (3) documentação e fechamento. O dono aprova cada parte ("Sim, parte N").
3. Registrar o plano da sprint no CLAUDE.md **antes** de implementar; ao fechar, atualizar CLAUDE.md, README e `docs/` e marcar "Verificado".
4. Verificar cada critério de aceite e conferir telas no navegador (desktop e celular).
5. **Commitar localmente e perguntar antes de enviar ao GitHub.** Mensagens de commit terminam com a linha de coautoria do Claude.
6. Não refatorar sem pedido; respeitar o escopo.
