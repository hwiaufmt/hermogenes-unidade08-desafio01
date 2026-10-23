from fastapi import APIRouter, HTTPException, Request, Response, status

from app.dependencias import DbSessao, UsuarioLogado
from app.schemas import LoginEntrada, UsuarioSaida
from app.services import usuarios

router = APIRouter(tags=["autenticação"])


@router.post("/login", response_model=UsuarioSaida)
def entrar(dados: LoginEntrada, request: Request, db: DbSessao):
    try:
        usuario = usuarios.autenticar(db, dados.cpf, dados.senha)
    except usuarios.CredenciaisInvalidasError as erro:
        raise HTTPException(status_code=401, detail=str(erro)) from erro
    request.session.clear()
    request.session["usuario_id"] = usuario.id
    return usuario


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def sair(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UsuarioSaida)
def eu(usuario: UsuarioLogado):
    return usuario
