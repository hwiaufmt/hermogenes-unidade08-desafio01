from fastapi.testclient import TestClient

from app.services.estoque import chave_alfabetica


def _criar_categoria(client: TestClient, nome: str) -> int:
    resposta = client.post("/categorias", json={"nome": nome})
    assert resposta.status_code == 201
    return resposta.json()["id"]


def _cadastrar(client: TestClient, categoria_id: int, nome: str) -> None:
    resposta = client.post(
        "/materiais", json={"nome": nome, "categoria_id": categoria_id}
    )
    assert resposta.status_code == 201


def _popular(client: TestClient) -> None:
    """Categorias e materiais com maiúsculas e acentos misturados, de propósito."""
    zebra = _criar_categoria(client, "zebra")
    agua = _criar_categoria(client, "Água")
    for nome in ("Zinco", "ábaco", "abacate", "Borracha", "borda"):
        _cadastrar(client, agua, nome)
    for nome in ("Listra", "arame"):
        _cadastrar(client, zebra, nome)


def _pares_da_lista(client: TestClient) -> list[tuple[str, str]]:
    return [
        (m["categoria"]["nome"], m["nome"]) for m in client.get("/materiais").json()
    ]


def _pares_dos_saldos(client: TestClient) -> list[tuple[str, str]]:
    return [
        (saldo["categoria"]["nome"], material["nome"])
        for saldo in client.get("/saldos").json()["categorias"]
        for material in saldo["materiais"]
    ]


def test_ca17_chave_ignora_maiusculas_e_acentos() -> None:
    assert chave_alfabetica("Água")[0] == chave_alfabetica("agua")[0] == "agua"
    nomes = ["zebra", "Água", "abacate", "Árvore", "Borracha"]

    assert sorted(nomes, key=chave_alfabetica) == [
        "abacate",
        "Água",
        "Árvore",
        "Borracha",
        "zebra",
    ]


def test_ca17_chave_desempata_de_forma_estavel_quando_so_o_acento_difere() -> None:
    nomes = ["Informática", "Informatica"]

    assert sorted(nomes, key=chave_alfabetica) == ["Informatica", "Informática"]
    assert sorted(reversed(nomes), key=chave_alfabetica) == [
        "Informatica",
        "Informática",
    ]


def test_ca17_lista_de_materiais_vem_por_categoria_e_depois_por_nome(
    client: TestClient,
) -> None:
    _popular(client)

    assert _pares_da_lista(client) == [
        ("Água", "abacate"),
        ("Água", "ábaco"),
        ("Água", "borda"),
        ("Água", "Borracha"),
        ("Água", "Zinco"),
        ("zebra", "arame"),
        ("zebra", "Listra"),
    ]


def test_ca17_saldos_e_lista_de_materiais_usam_a_mesma_ordem(
    client: TestClient,
) -> None:
    _popular(client)

    assert _pares_dos_saldos(client) == _pares_da_lista(client)


def test_ca17_lista_de_categorias_ignora_maiusculas_e_acentos(
    client: TestClient,
) -> None:
    _criar_categoria(client, "zebra")
    _criar_categoria(client, "Água")
    _criar_categoria(client, "beta")

    nomes = [c["nome"] for c in client.get("/categorias").json()]

    assert nomes == ["Água", "beta", "Escrita", "Informática", "Papelaria", "zebra"]


def test_ca17_categorias_dos_saldos_seguem_a_mesma_ordem_da_lista(
    client: TestClient,
) -> None:
    _criar_categoria(client, "zebra")
    _criar_categoria(client, "Água")

    da_lista = [c["nome"] for c in client.get("/categorias").json()]
    dos_saldos = [
        s["categoria"]["nome"] for s in client.get("/saldos").json()["categorias"]
    ]

    assert dos_saldos == da_lista


def test_ca17_filtros_da_lista_mantem_a_ordem(client: TestClient) -> None:
    _popular(client)

    resposta = client.get("/materiais", params={"q": "b"}).json()

    assert [m["nome"] for m in resposta] == ["abacate", "ábaco", "borda", "Borracha"]
