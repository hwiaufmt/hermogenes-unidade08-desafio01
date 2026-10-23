from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient


def test_ca03_saida_bloqueada_por_saldo_insuficiente(
    client: TestClient,
    criar_material: Callable[..., int],
    contar_movimentacoes: Callable[[], int],
) -> None:
    material_id = criar_material(quantidade=5)

    resposta = client.post(f"/materiais/{material_id}/saida", json={"quantidade": 6})

    assert resposta.status_code == 409
    assert "Saldo insuficiente" in resposta.json()["detail"]
    assert client.get(f"/materiais/{material_id}").json()["quantidade"] == 5
    assert contar_movimentacoes() == 0


def test_ca03_saida_em_material_sem_saldo_e_bloqueada(
    client: TestClient,
    criar_material: Callable[..., int],
    contar_movimentacoes: Callable[[], int],
) -> None:
    material_id = criar_material(quantidade=0)

    resposta = client.post(f"/materiais/{material_id}/saida", json={"quantidade": 1})

    assert resposta.status_code == 409
    assert contar_movimentacoes() == 0


def test_ca04_saida_deduz_do_saldo_anterior(
    client: TestClient,
    criar_material: Callable[..., int],
    contar_movimentacoes: Callable[[], int],
) -> None:
    material_id = criar_material(quantidade=10)

    resposta = client.post(f"/materiais/{material_id}/saida", json={"quantidade": 4})

    assert resposta.status_code == 200
    assert resposta.json()["quantidade"] == 6
    assert client.get(f"/materiais/{material_id}").json()["quantidade"] == 6
    assert contar_movimentacoes() == 1


def test_ca04_saida_igual_ao_saldo_zera_o_material(
    client: TestClient, criar_material: Callable[..., int]
) -> None:
    material_id = criar_material(quantidade=5)

    resposta = client.post(f"/materiais/{material_id}/saida", json={"quantidade": 5})

    assert resposta.status_code == 200
    assert resposta.json()["quantidade"] == 0


@pytest.mark.parametrize("quantidade", [0, -1, 2.5, "3", None])
def test_saida_rejeita_quantidade_invalida(
    client: TestClient,
    criar_material: Callable[..., int],
    contar_movimentacoes: Callable[[], int],
    quantidade: object,
) -> None:
    material_id = criar_material(quantidade=5)

    resposta = client.post(
        f"/materiais/{material_id}/saida", json={"quantidade": quantidade}
    )

    assert resposta.status_code == 422
    assert client.get(f"/materiais/{material_id}").json()["quantidade"] == 5
    assert contar_movimentacoes() == 0


def test_saida_em_material_inexistente_retorna_404(
    client: TestClient, contar_movimentacoes: Callable[[], int]
) -> None:
    resposta = client.post("/materiais/999/saida", json={"quantidade": 1})

    assert resposta.status_code == 404
    assert "não existe" in resposta.json()["detail"]
    assert contar_movimentacoes() == 0
