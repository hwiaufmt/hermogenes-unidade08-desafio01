from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencias import exigir
from app.permissoes import Acao
from app.schemas import MaterialSaida, MovimentacaoCriar
from app.services import estoque

router = APIRouter(
    prefix="/materiais",
    tags=["movimentações"],
    dependencies=[Depends(exigir(Acao.MOVIMENTAR))],
)

DbSessao = Annotated[Session, Depends(get_db)]


@router.post("/{material_id:int}/entrada", response_model=MaterialSaida)
def entrada(material_id: int, dados: MovimentacaoCriar, db: DbSessao):
    try:
        return estoque.registrar_entrada(db, material_id, dados.quantidade)
    except estoque.MaterialInexistenteError as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro


@router.post("/{material_id:int}/saida", response_model=MaterialSaida)
def saida(material_id: int, dados: MovimentacaoCriar, db: DbSessao):
    try:
        return estoque.registrar_saida(db, material_id, dados.quantidade)
    except estoque.MaterialInexistenteError as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro
    except estoque.SaldoInsuficienteError as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
