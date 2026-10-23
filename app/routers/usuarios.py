from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencias import exigir
from app.permissoes import Acao
from app.schemas import UsuarioAtualizar, UsuarioCriar, UsuarioSaida
from app.services import usuarios

router = APIRouter(
    prefix="/usuarios",
    tags=["usuários"],
    dependencies=[Depends(exigir(Acao.GERIR_USUARIOS))],
)

DbSessao = Annotated[Session, Depends(get_db)]


def _nao_encontrado(erro: Exception) -> HTTPException:
    return HTTPException(status_code=404, detail=str(erro))


def _conflito(erro: Exception) -> HTTPException:
    return HTTPException(status_code=409, detail=str(erro))


@router.get("", response_model=list[UsuarioSaida])
def listar(db: DbSessao):
    return usuarios.listar_usuarios(db)


@router.get("/{usuario_id:int}", response_model=UsuarioSaida)
def obter(usuario_id: int, db: DbSessao):
    try:
        return usuarios.obter_usuario(db, usuario_id)
    except usuarios.UsuarioInexistenteError as erro:
        raise _nao_encontrado(erro) from erro


@router.post("", response_model=UsuarioSaida, status_code=status.HTTP_201_CREATED)
def criar(dados: UsuarioCriar, db: DbSessao):
    try:
        return usuarios.criar_usuario(
            db, dados.nome, dados.cpf, dados.email, dados.perfil, dados.senha
        )
    except usuarios.CpfDuplicadoError as erro:
        raise _conflito(erro) from erro


@router.put("/{usuario_id:int}", response_model=UsuarioSaida)
def atualizar(usuario_id: int, dados: UsuarioAtualizar, db: DbSessao):
    try:
        return usuarios.atualizar_usuario(
            db, usuario_id, dados.nome, dados.email, dados.perfil, dados.senha
        )
    except usuarios.UsuarioInexistenteError as erro:
        raise _nao_encontrado(erro) from erro
    except usuarios.UltimoAdministradorError as erro:
        raise _conflito(erro) from erro


@router.post("/{usuario_id:int}/inativar", response_model=UsuarioSaida)
def inativar(usuario_id: int, db: DbSessao):
    try:
        return usuarios.inativar_usuario(db, usuario_id)
    except usuarios.UsuarioInexistenteError as erro:
        raise _nao_encontrado(erro) from erro
    except usuarios.UltimoAdministradorError as erro:
        raise _conflito(erro) from erro


@router.post("/{usuario_id:int}/reativar", response_model=UsuarioSaida)
def reativar(usuario_id: int, db: DbSessao):
    try:
        return usuarios.reativar_usuario(db, usuario_id)
    except usuarios.UsuarioInexistenteError as erro:
        raise _nao_encontrado(erro) from erro
