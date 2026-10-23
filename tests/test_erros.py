from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient


def _detalhe(resposta) -> str:
    assert resposta.status_code == 422
    detalhe = resposta.json()["detail"]
    assert isinstance(detalhe, str)
    return detalhe


@pytest.mark.parametrize(
    ("corpo", "esperado"),
    [
        ({"nome": "Lápis"}, "Selecione uma categoria."),
        ({"nome": "Lápis", "categoria_id": None}, "Selecione uma categoria."),
        ({"categoria_id": 1}, "O campo 'nome' é obrigatório."),
        ({"nome": "  ", "categoria_id": 1}, "O nome do material é obrigatório."),
        (
            {"nome": "Lápis", "categoria_id": 1, "quantidade": -1},
            "O campo 'quantidade' deve ser maior ou igual a 0.",
        ),
        (
            {"nome": "Lápis", "categoria_id": 1, "estoque_minimo": -1},
            "O campo 'estoque mínimo' deve ser maior ou igual a 0.",
        ),
        (
            {"nome": "Lápis", "categoria_id": 1, "quantidade": 1.5},
            "O campo 'quantidade' deve ser um número inteiro.",
        ),
        ({"nome": 123, "categoria_id": 1}, "O campo 'nome' deve ser um texto."),
    ],
)
def test_cadastro_devolve_mensagem_de_validacao_em_portugues(
    client: TestClient, corpo: dict, esperado: str
) -> None:
    assert _detalhe(client.post("/materiais", json=corpo)) == esperado


@pytest.mark.parametrize(
    ("corpo", "esperado"),
    [
        ({}, "O campo 'quantidade' é obrigatório."),
        ({"quantidade": 0}, "A quantidade deve ser um número inteiro maior que zero."),
        ({"quantidade": "3"}, "O campo 'quantidade' deve ser um número inteiro."),
        ({"quantidade": 2.5}, "O campo 'quantidade' deve ser um número inteiro."),
    ],
)
def test_movimentacao_devolve_mensagem_de_validacao_em_portugues(
    client: TestClient,
    criar_material: Callable[..., int],
    corpo: dict,
    esperado: str,
) -> None:
    material_id = criar_material(quantidade=5)

    for rota in ("entrada", "saida"):
        resposta = client.post(f"/materiais/{material_id}/{rota}", json=corpo)
        assert _detalhe(resposta) == esperado


def test_categoria_devolve_mensagem_de_validacao_em_portugues(
    client: TestClient,
) -> None:
    assert (
        _detalhe(client.post("/categorias", json={})) == "O campo 'nome' é obrigatório."
    )
    assert (
        _detalhe(client.post("/categorias", json={"nome": "  "}))
        == "O nome da categoria é obrigatório."
    )


def test_json_invalido_devolve_mensagem_em_portugues(client: TestClient) -> None:
    resposta = client.post(
        "/categorias",
        content="{nao e json",
        headers={"Content-Type": "application/json"},
    )

    assert _detalhe(resposta) == "O corpo da requisição não é um JSON válido."
