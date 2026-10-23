from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencias import exigir
from app.permissoes import Acao
from app.schemas import MaterialCriar, MaterialSaida
from app.services import estoque

router = APIRouter(prefix="/materiais", tags=["materiais"])

DbSessao = Annotated[Session, Depends(get_db)]

# A lista de materiais também apoia a tela Movimentar.
LER_MATERIAIS = exigir(Acao.CONSULTAR_ESTOQUE, Acao.MOVIMENTAR)


@router.get(
    "", response_model=list[MaterialSaida], dependencies=[Depends(LER_MATERIAIS)]
)
def listar(
    db: DbSessao,
    categoria_id: int | None = None,
    q: str | None = None,
    status: Literal["Disponível", "Indisponível"] | None = None,
):
    try:
        return estoque.listar_materiais(db, categoria_id, busca=q, status=status)
    except estoque.CategoriaInexistenteError as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro


@router.get(
    "/{material_id:int}",
    response_model=MaterialSaida,
    dependencies=[Depends(LER_MATERIAIS)],
)
def obter(material_id: int, db: DbSessao):
    try:
        return estoque.obter_material(db, material_id)
    except estoque.MaterialInexistenteError as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro


@router.post(
    "",
    response_model=MaterialSaida,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir(Acao.CADASTRAR_MATERIAL))],
)
def criar(dados: MaterialCriar, db: DbSessao):
    try:
        return estoque.criar_material(
            db,
            nome=dados.nome,
            categoria_id=dados.categoria_id,
            quantidade=dados.quantidade,
            estoque_minimo=dados.estoque_minimo,
        )
    except estoque.CategoriaInexistenteError as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro
