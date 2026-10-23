from collections.abc import Callable, Iterator

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from starlette.middleware.sessions import SessionMiddleware

from app import permissoes
from app.database import get_db
from app.dependencias import exigir
from app.permissoes import Acao, perfil_pode
from app.routers import autenticacao
from app.services.usuarios import (
    PERFIL_ADMINISTRADOR,
    PERFIL_ESTOQUISTA,
    PERFIL_OPERADOR,
    PERFIS,
    criar_usuario,
)

SENHA = "senha-segura-1"
CPFS = {
    PERFIL_ADMINISTRADOR: "52998224725",
    PERFIL_ESTOQUISTA: "11144477735",
    PERFIL_OPERADOR: "12345678909",
}
MATRIZ_DE_TESTE = {
    PERFIL_ADMINISTRADOR: frozenset({Acao.GERIR_USUARIOS}),
    PERFIL_ESTOQUISTA: frozenset({Acao.CADASTRAR_MATERIAL}),
    PERFIL_OPERADOR: frozenset({Acao.MOVIMENTAR}),
}


@pytest.fixture(autouse=True)
def matriz_de_teste(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(permissoes, "PERMISSOES", MATRIZ_DE_TESTE)


@pytest.fixture
def cliente_mini(fabrica_sessao: sessionmaker[Session]) -> Iterator[TestClient]:
    """App mínimo só com login e rotas protegidas, para testar o mecanismo."""
    mini = FastAPI()
    mini.add_middleware(SessionMiddleware, secret_key="chave-de-teste")
    mini.include_router(autenticacao.router)

    @mini.get("/movimentar", dependencies=[Depends(exigir(Acao.MOVIMENTAR))])
    def rota_movimentar() -> dict:
        return {"ok": True}

    @mini.get(
        "/consulta",
        dependencies=[Depends(exigir(Acao.MOVIMENTAR, Acao.CADASTRAR_MATERIAL))],
    )
    def rota_qualquer_uma() -> dict:
        return {"ok": True}

    def override_get_db() -> Iterator[Session]:
        with fabrica_sessao() as db:
            yield db

    mini.dependency_overrides[get_db] = override_get_db
    with fabrica_sessao() as db:
        for perfil, cpf in CPFS.items():
            criar_usuario(
                db, perfil.title(), cpf, f"{perfil}@exemplo.com", perfil, SENHA
            )
    yield TestClient(mini)


@pytest.fixture
def entrar_como(cliente_mini: TestClient) -> Callable[[str], None]:
    def entrar(perfil: str) -> None:
        resposta = cliente_mini.post(
            "/login", json={"cpf": CPFS[perfil], "senha": SENHA}
        )
        assert resposta.status_code == 200

    return entrar


def test_rota_protegida_sem_login_retorna_401(cliente_mini: TestClient) -> None:
    resposta = cliente_mini.get("/movimentar")

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "É necessário entrar no sistema."


def test_perfil_sem_a_acao_recebe_403(
    cliente_mini: TestClient, entrar_como: Callable[[str], None]
) -> None:
    entrar_como(PERFIL_ESTOQUISTA)

    resposta = cliente_mini.get("/movimentar")

    assert resposta.status_code == 403
    assert (
        resposta.json()["detail"] == "Você não tem permissão para realizar esta ação."
    )


def test_perfil_com_a_acao_acessa(
    cliente_mini: TestClient, entrar_como: Callable[[str], None]
) -> None:
    entrar_como(PERFIL_OPERADOR)

    assert cliente_mini.get("/movimentar").status_code == 200


def test_rota_com_varias_acoes_aceita_qualquer_uma_delas(
    cliente_mini: TestClient, entrar_como: Callable[[str], None]
) -> None:
    entrar_como(PERFIL_OPERADOR)
    assert cliente_mini.get("/consulta").status_code == 200

    entrar_como(PERFIL_ESTOQUISTA)
    assert cliente_mini.get("/consulta").status_code == 200

    entrar_como(PERFIL_ADMINISTRADOR)
    assert cliente_mini.get("/consulta").status_code == 403


def test_perfil_pode_exige_pelo_menos_uma_das_acoes() -> None:
    assert perfil_pode(PERFIL_OPERADOR, Acao.MOVIMENTAR)
    assert perfil_pode(PERFIL_OPERADOR, Acao.GERIR_USUARIOS, Acao.MOVIMENTAR)
    assert not perfil_pode(PERFIL_OPERADOR, Acao.GERIR_USUARIOS)
    assert not perfil_pode("perfil-desconhecido", Acao.MOVIMENTAR)


def test_matriz_oficial_tem_uma_entrada_para_cada_perfil(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.undo()

    assert set(permissoes.PERMISSOES) == set(PERFIS)
    assert all(isinstance(a, Acao) for p in permissoes.PERMISSOES.values() for a in p)
