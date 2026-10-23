from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Usuario
from app.permissoes import Acao, perfil_pode

DbSessao = Annotated[Session, Depends(get_db)]


def usuario_da_sessao(request: Request, db: Session) -> Usuario | None:
    """Usuário ativo da sessão, ou None. Relê o banco a cada requisição: inativar
    um usuário encerra o acesso dele imediatamente, mesmo com o cookie válido."""
    usuario_id = request.session.get("usuario_id")
    usuario = db.get(Usuario, usuario_id) if usuario_id is not None else None
    return usuario if usuario is not None and usuario.ativo else None


def usuario_atual(request: Request, db: DbSessao) -> Usuario:
    usuario = usuario_da_sessao(request, db)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="É necessário entrar no sistema.",
        )
    return usuario


UsuarioLogado = Annotated[Usuario, Depends(usuario_atual)]


def exigir(*acoes: Acao) -> Callable[[Usuario], Usuario]:
    """Dependência que exige login e que o perfil tenha ao menos uma das ações."""

    def verificar(usuario: UsuarioLogado) -> Usuario:
        if not perfil_pode(usuario.perfil, *acoes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para realizar esta ação.",
            )
        return usuario

    return verificar
