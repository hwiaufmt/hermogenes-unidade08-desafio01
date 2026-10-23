"""Matriz de permissões: o que cada perfil pode fazer.

Cada `Acao` abaixo corresponde a um conjunto de rotas e telas:

- GERIR_USUARIOS: /usuarios (criar, listar, editar, inativar, reativar);
  tela Usuários.
- CRIAR_CATEGORIA: POST /categorias; tela Cadastro.
- CADASTRAR_MATERIAL: POST /materiais (inclui estoque inicial e mínimo);
  tela Cadastro.
- MOVIMENTAR: POST /materiais/{id}/entrada e /saida; tela Movimentar.
- CONSULTAR_ESTOQUE: GET /materiais e GET /materiais/{id}; tela Pesquisa.

Leituras que servem de apoio a outras telas aceitam "qualquer uma de" várias
ações: GET /categorias é liberado a quem consulta, cadastra material ou cria
categoria; a lista de materiais também é liberada a quem movimenta.
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
    CADASTRAR_MATERIAL = "cadastrar_material"
    MOVIMENTAR = "movimentar"
    CONSULTAR_ESTOQUE = "consultar_estoque"


# TODO(você): defina o que cada perfil pode fazer.
#
# Regras que você descreveu:
#   - Estoquista: informa valores de estoque, cadastra materiais e categorias.
#   - Operador: apenas movimenta materiais e usa a tela de pesquisa.
#   - Administrador: mantém os usuários (perfil criado por decisão sua).
#
# Pontos em aberto para decidir ao escrever:
#   1. O estoquista deve poder CONSULTAR_ESTOQUE? Sem isso ele cadastra
#      materiais "às cegas", sem ver a lista.
#   2. O administrador também faz o trabalho de estoque, ou só gere usuários?
#   3. Usar frozenset({Acao.X, Acao.Y}) em cada perfil.
#
# Enquanto estiver vazio, ninguém tem permissão para nada (falha segura).
PERMISSOES: dict[str, frozenset[Acao]] = {
    PERFIL_ADMINISTRADOR: frozenset(),
    PERFIL_ESTOQUISTA: frozenset(),
    PERFIL_OPERADOR: frozenset(),
}


def perfil_pode(perfil: str, *acoes: Acao) -> bool:
    """True se o perfil tem **pelo menos uma** das ações informadas."""
    permitidas = PERMISSOES.get(perfil, frozenset())
    return any(acao in permitidas for acao in acoes)
