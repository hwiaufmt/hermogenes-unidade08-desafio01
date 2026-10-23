from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencias import exigir
from app.permissoes import Acao
from app.schemas import CategoriaCriar, CategoriaSaida
from app.services import estoque

router = APIRouter(prefix="/categorias", tags=["categorias"])

DbSessao = Annotated[Session, Depends(get_db)]

# A lista de categorias apoia os formulários e filtros de várias telas.
LER_CATEGORIAS = exigir(
    Acao.CONSULTAR_ESTOQUE, Acao.CADASTRAR_MATERIAL, Acao.CRIAR_CATEGORIA
)


@router.get(
    "", response_model=list[CategoriaSaida], dependencies=[Depends(LER_CATEGORIAS)]
)
def listar(db: DbSessao):
    return estoque.listar_categorias(db)


@router.post(
    "",
    response_model=CategoriaSaida,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir(Acao.CRIAR_CATEGORIA))],
)
def criar(dados: CategoriaCriar, db: DbSessao):
    try:
        return estoque.criar_categoria(db, dados.nome)
    except estoque.CategoriaDuplicadaError as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro
