from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import CategoriaCriar, CategoriaSaida
from app.services import estoque

router = APIRouter(prefix="/categorias", tags=["categorias"])

DbSessao = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[CategoriaSaida])
def listar(db: DbSessao):
    return estoque.listar_categorias(db)


@router.post("", response_model=CategoriaSaida, status_code=status.HTTP_201_CREATED)
def criar(dados: CategoriaCriar, db: DbSessao):
    try:
        return estoque.criar_categoria(db, dados.nome)
    except estoque.CategoriaDuplicadaError as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro
