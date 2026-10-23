from collections.abc import Callable

from fastapi.testclient import TestClient


def test_fluxo_completo_cadastrar_movimentar_e_consultar(
    client: TestClient, contar_movimentacoes: Callable[[], int]
) -> None:
    # Nova categoria pela interface e uma do seed.
    limpeza = client.post("/categorias", json={"nome": "Limpeza"}).json()["id"]
    papelaria = next(
        c["id"] for c in client.get("/categorias").json() if c["nome"] == "Papelaria"
    )

    # Cadastro: categoria inexistente é rejeitada; válida é aceita.
    assert (
        client.post(
            "/materiais", json={"nome": "Detergente", "categoria_id": 999}
        ).status_code
        == 422
    )
    detergente = client.post(
        "/materiais",
        json={"nome": "Detergente", "categoria_id": limpeza, "quantidade": 5},
    ).json()["id"]
    client.post("/materiais", json={"nome": "Resma A4", "categoria_id": papelaria})

    # Entrada soma ao saldo.
    corpo = client.post(
        f"/materiais/{detergente}/entrada", json={"quantidade": 3}
    ).json()
    assert corpo["quantidade"] == 8
    assert corpo["status"] == "Disponível"

    # Saída acima do saldo é bloqueada e nada muda.
    movimentacoes_antes = contar_movimentacoes()
    bloqueada = client.post(f"/materiais/{detergente}/saida", json={"quantidade": 9})
    assert bloqueada.status_code == 409
    assert client.get(f"/materiais/{detergente}").json()["quantidade"] == 8
    assert contar_movimentacoes() == movimentacoes_antes

    # Saída total zera o saldo e o status vira Indisponível.
    corpo = client.post(f"/materiais/{detergente}/saida", json={"quantidade": 8}).json()
    assert corpo["quantidade"] == 0
    assert corpo["status"] == "Indisponível"

    # Nova entrada devolve o status Disponível.
    corpo = client.post(
        f"/materiais/{detergente}/entrada", json={"quantidade": 2}
    ).json()
    assert corpo["quantidade"] == 2
    assert corpo["status"] == "Disponível"

    # Consulta: todos, filtrados por categoria e por categoria sem material.
    todos = {m["nome"]: m for m in client.get("/materiais").json()}
    assert todos["Detergente"]["categoria"]["nome"] == "Limpeza"
    assert todos["Resma A4"]["status"] == "Indisponível"

    filtrados = client.get("/materiais", params={"categoria_id": limpeza}).json()
    assert [m["nome"] for m in filtrados] == ["Detergente"]

    escrita = next(
        c["id"] for c in client.get("/categorias").json() if c["nome"] == "Escrita"
    )
    assert client.get("/materiais", params={"categoria_id": escrita}).json() == []

    # Três movimentações válidas gravadas: entrada, saída total e entrada.
    assert contar_movimentacoes() == 3
