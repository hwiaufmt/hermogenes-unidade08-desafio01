from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Movimentacao
from app.services.estoque import semear_categorias


@pytest.fixture
def fabrica_sessao() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    fabrica = sessionmaker(bind=engine, expire_on_commit=False)
    with fabrica() as db:
        semear_categorias(db)
    return fabrica


@pytest.fixture
def client(fabrica_sessao: sessionmaker[Session]) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        with fabrica_sessao() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def criar_material(client: TestClient) -> Callable[..., int]:
    def criar(nome: str = "Caneta", quantidade: int = 0) -> int:
        categoria_id = client.get("/categorias").json()[0]["id"]
        resposta = client.post(
            "/materiais",
            json={"nome": nome, "categoria_id": categoria_id, "quantidade": quantidade},
        )
        return resposta.json()["id"]

    return criar


@pytest.fixture
def contar_movimentacoes(
    fabrica_sessao: sessionmaker[Session],
) -> Callable[[], int]:
    def contar() -> int:
        with fabrica_sessao() as db:
            return db.scalar(select(func.count()).select_from(Movimentacao))

    return contar
