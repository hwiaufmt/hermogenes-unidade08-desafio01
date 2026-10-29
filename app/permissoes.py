"""Matriz de permissões: o que cada perfil pode fazer.

Cada `Acao` abaixo corresponde a um conjunto de rotas e telas:

- GERIR_USUARIOS: /usuarios (criar, listar, editar, inativar, reativar);
  tela Usuários.
- CRIAR_CATEGORIA: POST /categorias; tela Cadastro.
- EDITAR_CATEGORIA: PUT /categorias/{id} (altera o nome; com materiais exige
  confirmação); tela Cadastro.
- CADASTRAR_MATERIAL: POST /materiais (inclui estoque inicial e mínimo);
  tela Cadastro.
- MOVIMENTAR: POST /materiais/{id}/entrada e /saida; tela Movimentar.
- CONSULTAR_ESTOQUE: GET /materiais, GET /materiais/{id} e GET /saldos;
  telas Pesquisa e Saldos.

Leituras que servem de apoio a outras telas aceitam "qualquer uma de" várias
ações: GET /categorias é liberado a quem consulta, cadastra material, cria ou
edita categoria; a lista de materiais também é liberada a quem movimenta.
"""

from enum import StrEnum

from app.services.usuarios import (
    PERFIL_ADMINISTRADOR,
    PERFIL_ESTOQUISTA,
    PERFIL_OPERADOR,
)


class Acao(StrEnum):
    GERIR_USUARIOS = "gerir_usuarios"
    CRIAR_CATEGORIA = "criar_categoria"
    EDITAR_CATEGORIA = "editar_categoria"
    CADASTRAR_MATERIAL = "cadastrar_material"
    MOVIMENTAR = "movimentar"
    CONSULTAR_ESTOQUE = "consultar_estoque"


# Quem pode o quê:
#   - Estoquista: informa valores de estoque (estoque inicial e mínimo no
#     cadastro), cadastra materiais, cria e edita categorias, e consulta o
#     estoque.
#   - Operador: movimenta materiais e consulta o estoque (tela de pesquisa).
#   - Administrador: apenas mantém os usuários.
#
# Perfil ausente deste dicionário, ou com conjunto vazio, não pode nada
# (falha segura).
PERMISSOES: dict[str, frozenset[Acao]] = {
    PERFIL_ADMINISTRADOR: frozenset({Acao.GERIR_USUARIOS}),
    PERFIL_ESTOQUISTA: frozenset(
        {
            Acao.CRIAR_CATEGORIA,
            Acao.EDITAR_CATEGORIA,
            Acao.CADASTRAR_MATERIAL,
            Acao.CONSULTAR_ESTOQUE,
        }
    ),
    PERFIL_OPERADOR: frozenset({Acao.MOVIMENTAR, Acao.CONSULTAR_ESTOQUE}),
}


def perfil_pode(perfil: str, *acoes: Acao) -> bool:
    """True se o perfil tem **pelo menos uma** das ações informadas."""
    permitidas = PERMISSOES.get(perfil, frozenset())
    return any(acao in permitidas for acao in acoes)
