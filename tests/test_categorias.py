from fastapi.testclient import TestClient


def test_listar_categorias_retorna_seed(client: TestClient) -> None:
    resposta = client.get("/categorias")

    assert resposta.status_code == 200
    nomes = [c["nome"] for c in resposta.json()]
    assert nomes == ["Escrita", "Informática", "Papelaria"]


def test_criar_categoria_nova(client: TestClient) -> None:
    resposta = client.post("/categorias", json={"nome": "  Limpeza "})

    assert resposta.status_code == 201
    assert resposta.json()["nome"] == "Limpeza"
    nomes = [c["nome"] for c in client.get("/categorias").json()]
    assert "Limpeza" in nomes


def test_criar_categoria_duplicada_retorna_422(client: TestClient) -> None:
    resposta = client.post("/categorias", json={"nome": "Papelaria"})

    assert resposta.status_code == 422
    assert "Papelaria" in resposta.json()["detail"]
    assert len(client.get("/categorias").json()) == 3


def test_criar_categoria_vazia_retorna_422(client: TestClient) -> None:
    resposta = client.post("/categorias", json={"nome": "   "})

    assert resposta.status_code == 422
    assert len(client.get("/categorias").json()) == 3
