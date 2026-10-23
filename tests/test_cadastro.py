from fastapi.testclient import TestClient


def _id_categoria(client: TestClient, nome: str) -> int:
    categorias = client.get("/categorias").json()
    return next(c["id"] for c in categorias if c["nome"] == nome)


def test_ca01_cadastra_material_com_categoria_valida(client: TestClient) -> None:
    categoria_id = _id_categoria(client, "Papelaria")

    resposta = client.post(
        "/materiais",
        json={"nome": "Resma A4", "categoria_id": categoria_id, "quantidade": 10},
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["nome"] == "Resma A4"
    assert corpo["categoria"]["nome"] == "Papelaria"
    assert corpo["quantidade"] == 10
    assert corpo["status"] == "Disponível"
    assert len(client.get("/materiais").json()) == 1


def test_ca01_rejeita_categoria_inexistente(client: TestClient) -> None:
    resposta = client.post("/materiais", json={"nome": "Caneta", "categoria_id": 999})

    assert resposta.status_code == 422
    assert "não existe" in resposta.json()["detail"]
    assert client.get("/materiais").json() == []


def test_ca01_rejeita_categoria_ausente(client: TestClient) -> None:
    resposta = client.post("/materiais", json={"nome": "Caneta"})

    assert resposta.status_code == 422
    assert client.get("/materiais").json() == []


def test_cadastro_rejeita_nome_vazio_e_valores_negativos(client: TestClient) -> None:
    categoria_id = _id_categoria(client, "Escrita")

    for dados in (
        {"nome": " ", "categoria_id": categoria_id},
        {"nome": "Lápis", "categoria_id": categoria_id, "quantidade": -1},
        {"nome": "Lápis", "categoria_id": categoria_id, "estoque_minimo": -1},
    ):
        assert client.post("/materiais", json=dados).status_code == 422

    assert client.get("/materiais").json() == []


def test_material_com_estoque_inicial_zero_nasce_indisponivel(
    client: TestClient,
) -> None:
    categoria_id = _id_categoria(client, "Informática")

    resposta = client.post(
        "/materiais", json={"nome": "Mouse", "categoria_id": categoria_id}
    )

    assert resposta.status_code == 201
    assert resposta.json()["quantidade"] == 0
    assert resposta.json()["status"] == "Indisponível"


def test_lista_materiais_filtra_por_categoria(client: TestClient) -> None:
    papelaria = _id_categoria(client, "Papelaria")
    escrita = _id_categoria(client, "Escrita")
    client.post("/materiais", json={"nome": "Resma A4", "categoria_id": papelaria})
    client.post("/materiais", json={"nome": "Caneta", "categoria_id": escrita})

    todos = client.get("/materiais").json()
    filtrados = client.get("/materiais", params={"categoria_id": escrita}).json()

    assert len(todos) == 2
    assert [m["nome"] for m in filtrados] == ["Caneta"]


def test_filtro_por_categoria_inexistente_retorna_404(client: TestClient) -> None:
    resposta = client.get("/materiais", params={"categoria_id": 999})

    assert resposta.status_code == 404
