"""Nome de categoria único, sem diferenciar maiúsculas de minúsculas."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Categoria
from app.services.estoque import semear_categorias


def _nomes(client: TestClient) -> list[str]:
    return [c["nome"] for c in client.get("/categorias").json()]


def _id(client: TestClient, nome: str) -> int:
    return next(c["id"] for c in client.get("/categorias").json() if c["nome"] == nome)


def _cadastrar(client: TestClient, nome: str, categoria: str) -> None:
    resposta = client.post(
        "/materiais",
        json={"nome": nome, "categoria_id": _id(client, categoria), "quantidade": 1},
    )
    assert resposta.status_code == 201


# ------------------------------------------------------------------ criar


@pytest.mark.parametrize(
    "nome", ["papelaria", "PAPELARIA", "pApElArIa", "  papelaria  "]
)
def test_criar_categoria_com_nome_existente_em_outra_caixa_e_recusado(
    client: TestClient, nome: str
) -> None:
    resposta = client.post("/categorias", json={"nome": nome})

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "Já existe uma categoria chamada 'Papelaria'."
    assert _nomes(client) == ["Escrita", "Informática", "Papelaria"]


@pytest.mark.parametrize("nome", ["informática", "INFORMÁTICA"])
def test_criar_categoria_sem_diferenciar_caixa_em_letras_acentuadas(
    client: TestClient, nome: str
) -> None:
    resposta = client.post("/categorias", json={"nome": nome})

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "Já existe uma categoria chamada 'Informática'."


def test_criar_categoria_repetida_em_outra_caixa_vale_tambem_para_as_novas(
    client: TestClient,
) -> None:
    client.post("/categorias", json={"nome": "Limpeza"})

    resposta = client.post("/categorias", json={"nome": "limpeza"})

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "Já existe uma categoria chamada 'Limpeza'."


def test_acento_continua_diferenciando_categorias(client: TestClient) -> None:
    resposta = client.post("/categorias", json={"nome": "Informatica"})

    assert resposta.status_code == 201


# ----------------------------------------------------------------- editar


@pytest.mark.parametrize("nome", ["papelaria", "PAPELARIA"])
def test_ca09_renomear_para_nome_de_outra_categoria_em_outra_caixa_e_recusado(
    client: TestClient, nome: str
) -> None:
    limpeza = client.post("/categorias", json={"nome": "Limpeza"}).json()["id"]

    resposta = client.put(f"/categorias/{limpeza}", json={"nome": nome})

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "Já existe uma categoria chamada 'Papelaria'."
    assert "Limpeza" in _nomes(client)


def test_ca09_nome_repetido_em_outra_caixa_e_recusado_antes_da_confirmacao(
    client: TestClient,
) -> None:
    _cadastrar(client, "Caneta", "Escrita")

    resposta = client.put(
        f"/categorias/{_id(client, 'Escrita')}", json={"nome": "PAPELARIA"}
    )

    assert resposta.status_code == 422
    assert "afetados" not in resposta.json()


def test_ca09_pode_mudar_apenas_a_caixa_do_proprio_nome(client: TestClient) -> None:
    limpeza = client.post("/categorias", json={"nome": "Limpeza"}).json()["id"]

    resposta = client.put(f"/categorias/{limpeza}", json={"nome": "LIMPEZA"})

    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "LIMPEZA"
    assert "LIMPEZA" in _nomes(client)


def test_ca10_mudar_so_a_caixa_de_categoria_com_materiais_tambem_pede_confirmacao(
    client: TestClient,
) -> None:
    _cadastrar(client, "Caneta", "Escrita")
    escrita = _id(client, "Escrita")

    sem_confirmar = client.put(f"/categorias/{escrita}", json={"nome": "escrita"})
    confirmado = client.put(
        f"/categorias/{escrita}", json={"nome": "escrita", "confirmar": True}
    )

    assert sem_confirmar.status_code == 409
    assert sem_confirmar.json()["afetados"] == 1
    assert confirmado.status_code == 200
    assert confirmado.json()["nome"] == "escrita"


# ------------------------------------------------------------------- seed


def test_seed_nao_recria_categoria_que_ja_existe_em_outra_caixa(
    fabrica_sessao: sessionmaker[Session],
) -> None:
    with fabrica_sessao() as db:
        papelaria = db.scalar(select(Categoria).where(Categoria.nome == "Papelaria"))
        papelaria.nome = "papelaria"
        db.commit()

        semear_categorias(db)

        nomes = sorted(c.nome for c in db.scalars(select(Categoria)))
        assert nomes == ["Escrita", "Informática", "papelaria"]
