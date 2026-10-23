from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import permissoes
from app.database import Base, get_db
from app.main import app
from app.models import Movimentacao, Usuario
from app.permissoes import Acao
from app.services.estoque import semear_categorias
from app.services.usuarios import (
    PERFIL_ADMINISTRADOR,
    PERFIL_ESTOQUISTA,
    PERFIL_OPERADOR,
    criar_usuario,
)

SENHA_DE_TESTE = "senha-de-teste-1"
CPFS_DE_TESTE = {
    PERFIL_ADMINISTRADOR: "39053344705",
    PERFIL_ESTOQUISTA: "98765432100",
    PERFIL_OPERADOR: "24681357928",
}


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
def cliente_anonimo(fabrica_sessao: sessionmaker[Session]) -> Iterator[TestClient]:
    """Cliente sem login, com banco em memória isolado."""

    def override_get_db() -> Iterator[Session]:
        with fabrica_sessao() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def entrar_como(
    cliente_anonimo: TestClient, fabrica_sessao: sessionmaker[Session]
) -> Callable[[str], TestClient]:
    """Entra no sistema como um usuário de teste do perfil informado."""

    def entrar(perfil: str) -> TestClient:
        cpf = CPFS_DE_TESTE[perfil]
        with fabrica_sessao() as db:
            if db.scalar(select(Usuario).where(Usuario.cpf == cpf)) is None:
                criar_usuario(
                    db, perfil.title(), cpf, f"{perfil}@teste.local", perfil,
                    SENHA_DE_TESTE,
                )  # fmt: skip
        resposta = cliente_anonimo.post(
            "/login", json={"cpf": cpf, "senha": SENHA_DE_TESTE}
        )
        assert resposta.status_code == 200, resposta.text
        return cliente_anonimo

    return entrar


@pytest.fixture
def client(
    cliente_anonimo: TestClient,
    entrar_como: Callable[[str], TestClient],
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    """Cliente logado com **todas** as permissões.

    Os testes de regra de negócio usam este cliente para não depender da matriz
    de permissões. As permissões reais são testadas em test_acesso_rotas.py.
    """
    monkeypatch.setattr(
        permissoes, "PERMISSOES", {PERFIL_ADMINISTRADOR: frozenset(Acao)}
    )
    return entrar_como(PERFIL_ADMINISTRADOR)


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
