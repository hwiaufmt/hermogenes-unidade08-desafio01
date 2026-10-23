from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient


def test_ca02_entrada_soma_ao_saldo_anterior(
    client: TestClient, criar_material: Callable[..., int]
) -> None:
    material_id = criar_material(quantidade=5)

    resposta = client.post(f"/materiais/{material_id}/entrada", json={"quantidade": 3})

    assert resposta.status_code == 200
    assert resposta.json()["quantidade"] == 8
    assert client.get(f"/materiais/{material_id}").json()["quantidade"] == 8


def test_ca02_entradas_sucessivas_acumulam(
    client: TestClient, criar_material: Callable[..., int]
) -> None:
    material_id = criar_material(quantidade=0)

    client.post(f"/materiais/{material_id}/entrada", json={"quantidade": 4})
    resposta = client.post(f"/materiais/{material_id}/entrada", json={"quantidade": 6})

    assert resposta.json()["quantidade"] == 10


def test_entrada_grava_movimentacao(
    client: TestClient,
    criar_material: Callable[..., int],
    contar_movimentacoes: Callable[[], int],
) -> None:
    material_id = criar_material(quantidade=5)

    client.post(f"/materiais/{material_id}/entrada", json={"quantidade": 3})

    assert contar_movimentacoes() == 1


@pytest.mark.parametrize("quantidade", [0, -1, 2.5, "3", None])
def test_entrada_rejeita_quantidade_invalida(
    client: TestClient,
    criar_material: Callable[..., int],
    contar_movimentacoes: Callable[[], int],
    quantidade: object,
) -> None:
    material_id = criar_material(quantidade=5)

    resposta = client.post(
        f"/materiais/{material_id}/entrada", json={"quantidade": quantidade}
    )

    assert resposta.status_code == 422
    assert client.get(f"/materiais/{material_id}").json()["quantidade"] == 5
    assert contar_movimentacoes() == 0


def test_entrada_em_material_inexistente_retorna_404(
    client: TestClient, contar_movimentacoes: Callable[[], int]
) -> None:
    resposta = client.post("/materiais/999/entrada", json={"quantidade": 1})

    assert resposta.status_code == 404
    assert "não existe" in resposta.json()["detail"]
    assert contar_movimentacoes() == 0
