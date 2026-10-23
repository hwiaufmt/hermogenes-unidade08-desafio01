from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Usuario

DbSessao = Annotated[Session, Depends(get_db)]


def usuario_atual(request: Request, db: DbSessao) -> Usuario:
    """Usuário da sessão. Relê o banco a cada requisição: inativar um usuário
    encerra o acesso dele imediatamente, mesmo com o cookie ainda válido."""
    usuario_id = request.session.get("usuario_id")
    usuario = db.get(Usuario, usuario_id) if usuario_id is not None else None
    if usuario is None or not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="É necessário entrar no sistema.",
        )
    return usuario


UsuarioLogado = Annotated[Usuario, Depends(usuario_atual)]
