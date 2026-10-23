from collections.abc import Callable

from fastapi.testclient import TestClient


def _cadastrar(client: TestClient, nome: str, categoria: str, quantidade: int) -> None:
    categorias = {c["nome"]: c["id"] for c in client.get("/categorias").json()}
    resposta = client.post(
        "/materiais",
        json={
            "nome": nome,
            "categoria_id": categorias[categoria],
            "quantidade": quantidade,
        },
    )
    assert resposta.status_code == 201


def _nomes(client: TestClient, **parametros: object) -> list[str]:
    resposta = client.get("/materiais", params=parametros)
    assert resposta.status_code == 200
    return [m["nome"] for m in resposta.json()]


def _preparar(client: TestClient) -> None:
    _cadastrar(client, "Caneta azul", "Escrita", 5)
    _cadastrar(client, "Caneta preta", "Escrita", 0)
    _cadastrar(client, "Lápis", "Escrita", 2)
    _cadastrar(client, "Resma A4", "Papelaria", 10)
    _cadastrar(client, "Mouse", "Informática", 0)


def test_pesquisa_por_parte_do_nome_ignora_maiusculas(client: TestClient) -> None:
    _preparar(client)

    assert _nomes(client, q="caneta") == ["Caneta azul", "Caneta preta"]
    assert _nomes(client, q="CANETA") == ["Caneta azul", "Caneta preta"]
    assert _nomes(client, q="a4") == ["Resma A4"]
    assert _nomes(client, q="inexistente") == []


def test_pesquisa_vazia_ou_so_espacos_nao_filtra(client: TestClient) -> None:
    _preparar(client)

    assert len(_nomes(client, q="")) == 5
    assert len(_nomes(client, q="   ")) == 5


def test_pesquisa_trata_percent_e_underscore_como_texto(client: TestClient) -> None:
    _cadastrar(client, "Desconto 10% off", "Papelaria", 1)
    _cadastrar(client, "Item_a", "Papelaria", 1)
    _cadastrar(client, "Itemxa", "Papelaria", 1)

    assert _nomes(client, q="%") == ["Desconto 10% off"]
    assert _nomes(client, q="_a") == ["Item_a"]


def test_pesquisa_por_status(client: TestClient) -> None:
    _preparar(client)

    assert _nomes(client, status="Indisponível") == ["Caneta preta", "Mouse"]
    assert _nomes(client, status="Disponível") == [
        "Caneta azul",
        "Lápis",
        "Resma A4",
    ]


def test_pesquisa_combina_nome_categoria_e_status(client: TestClient) -> None:
    _preparar(client)
    escrita = next(
        c["id"] for c in client.get("/categorias").json() if c["nome"] == "Escrita"
    )

    assert _nomes(client, q="caneta", categoria_id=escrita, status="Disponível") == [
        "Caneta azul"
    ]
    assert _nomes(client, categoria_id=escrita, status="Indisponível") == [
        "Caneta preta"
    ]
    assert _nomes(client, q="mouse", categoria_id=escrita) == []


def test_status_de_busca_invalido_devolve_422_em_portugues(
    client: TestClient,
) -> None:
    resposta = client.get("/materiais", params={"status": "Quebrado"})

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "Valor inválido no campo 'status'."


def test_resultado_da_busca_acompanha_a_movimentacao(
    client: TestClient, criar_material: Callable[..., int]
) -> None:
    material_id = criar_material("Grampeador", quantidade=1)
    assert _nomes(client, status="Indisponível") == []

    client.post(f"/materiais/{material_id}/saida", json={"quantidade": 1})

    assert _nomes(client, status="Indisponível") == ["Grampeador"]
