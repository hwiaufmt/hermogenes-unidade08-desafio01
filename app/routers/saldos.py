from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencias import exigir
from app.permissoes import Acao
from app.schemas import ConsultaDeSaldosSaida
from app.services import estoque

router = APIRouter(
    prefix="/saldos",
    tags=["saldos"],
    dependencies=[Depends(exigir(Acao.CONSULTAR_ESTOQUE))],
)

DbSessao = Annotated[Session, Depends(get_db)]


@router.get("", response_model=ConsultaDeSaldosSaida)
def consultar(db: DbSessao):
    return estoque.consultar_saldos(db)
