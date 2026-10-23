from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import CHAVE_SECRETA, DURACAO_SESSAO_SEGUNDOS
from app.database import Base, SessionLocal, engine
from app.erros import tratar_validacao
from app.routers import (
    autenticacao,
    categorias,
    materiais,
    movimentacoes,
    paginas,
    usuarios,
)
from app.services.estoque import semear_categorias

BASE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        semear_categorias(db)
    yield


app = FastAPI(title="Controle de Materiais de Escritório", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=CHAVE_SECRETA,
    max_age=DURACAO_SESSAO_SEGUNDOS,
    same_site="lax",
)
app.add_exception_handler(RequestValidationError, tratar_validacao)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.include_router(autenticacao.router)
app.include_router(categorias.router)
app.include_router(materiais.router)
app.include_router(movimentacoes.router)
app.include_router(usuarios.router)
app.include_router(paginas.router)


@app.get("/saude")
def saude() -> dict[str, str]:
    return {"status": "ok"}
