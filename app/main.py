import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.config import (
    ADMIN_CPF,
    ADMIN_EMAIL,
    ADMIN_NOME,
    ADMIN_SENHA,
    CHAVE_SECRETA,
    DURACAO_SESSAO_SEGUNDOS,
    SENHA_PADRAO,
)
from app.database import Base, SessionLocal, engine
from app.erros import tratar_validacao
from app.routers import (
    autenticacao,
    categorias,
    materiais,
    movimentacoes,
    paginas,
    saldos,
    usuarios,
)
from app.routers.paginas import (
    AcessoNegadoError,
    LoginNecessarioError,
    tratar_acesso_negado,
    tratar_login_necessario,
)
from app.services.estoque import semear_categorias
from app.services.usuarios import criar_administrador_inicial

BASE_DIR = Path(__file__).parent
registro = logging.getLogger("uvicorn.error")


def _criar_administrador_inicial(db: Session) -> None:
    criado = criar_administrador_inicial(
        db, ADMIN_CPF, ADMIN_SENHA, ADMIN_NOME, ADMIN_EMAIL
    )
    if criado:
        registro.info("Administrador inicial criado (CPF %s).", criado.cpf)
        if ADMIN_SENHA == SENHA_PADRAO:
            registro.warning(
                "O administrador usa a senha padrão do protótipo. "
                "Defina ESTOQUE_ADMIN_CPF e ESTOQUE_ADMIN_SENHA para trocar."
            )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        semear_categorias(db)
        _criar_administrador_inicial(db)
    yield


app = FastAPI(title="Controle de Materiais de Escritório", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=CHAVE_SECRETA,
    max_age=DURACAO_SESSAO_SEGUNDOS,
    same_site="lax",
)
app.add_exception_handler(RequestValidationError, tratar_validacao)
app.add_exception_handler(LoginNecessarioError, tratar_login_necessario)
app.add_exception_handler(AcessoNegadoError, tratar_acesso_negado)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.include_router(autenticacao.router)
app.include_router(categorias.router)
app.include_router(materiais.router)
app.include_router(movimentacoes.router)
app.include_router(saldos.router)
app.include_router(usuarios.router)
app.include_router(paginas.router)


@app.get("/saude")
def saude() -> dict[str, str]:
    return {"status": "ok"}
