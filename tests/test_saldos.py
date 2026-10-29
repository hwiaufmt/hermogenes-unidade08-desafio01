from collections.abc import Callable

from fastapi.testclient import TestClient


def _id(client: TestClient, nome: str) -> int:
    return next(c["id"] for c in client.get("/categorias").json() if c["nome"] == nome)


def _cadastrar(
    client: TestClient, nome: str, categoria: str, quantidade: int, minimo: int = 0
) -> int:
    resposta = client.post(
        "/materiais",
        json={
            "nome": nome,
            "categoria_id": _id(client, categoria),
            "quantidade": quantidade,
            "estoque_minimo": minimo,
        },
    )
    assert resposta.status_code == 201
    return resposta.json()["id"]


def _preparar(client: TestClient) -> dict[str, int]:
    return {
        "resma": _cadastrar(client, "Resma A4", "Papelaria", 10, minimo=4),
        "grampeador": _cadastrar(client, "Grampeador", "Papelaria", 0),
        "caneta": _cadastrar(client, "Caneta azul", "Escrita", 5, minimo=2),
    }


def _por_categoria(client: TestClient) -> dict[str, dict]:
    corpo = client.get("/saldos").json()
    return {c["categoria"]["nome"]: c for c in corpo["categorias"]}


def test_ca11_resumo_por_categoria_traz_materiais_unidades_e_indisponiveis(
    client: TestClient,
) -> None:
    _preparar(client)

    resumo = _por_categoria(client)

    assert resumo["Papelaria"]["total_materiais"] == 2
    assert resumo["Papelaria"]["total_unidades"] == 10
    assert resumo["Papelaria"]["total_indisponiveis"] == 1
    assert resumo["Escrita"]["total_materiais"] == 1
    assert resumo["Escrita"]["total_unidades"] == 5
    assert resumo["Escrita"]["total_indisponiveis"] == 0


def test_ca11_categoria_sem_materiais_aparece_com_zeros(client: TestClient) -> None:
    _preparar(client)

    informatica = _por_categoria(client)["Informática"]

    assert informatica["total_materiais"] == 0
    assert informatica["total_unidades"] == 0
    assert informatica["total_indisponiveis"] == 0
    assert informatica["materiais"] == []


def test_ca11_total_geral_soma_todas_as_categorias(client: TestClient) -> None:
    _preparar(client)

    corpo = client.get("/saldos").json()

    assert corpo["totais"] == {
        "total_materiais": 3,
        "total_unidades": 15,
        "total_indisponiveis": 1,
    }
    for campo in ("total_materiais", "total_unidades", "total_indisponiveis"):
        assert corpo["totais"][campo] == sum(c[campo] for c in corpo["categorias"])


def test_ca11_cada_material_traz_saldo_minimo_e_status(client: TestClient) -> None:
    ids = _preparar(client)

    materiais = {m["nome"]: m for m in _por_categoria(client)["Papelaria"]["materiais"]}

    assert materiais["Resma A4"] == {
        "id": ids["resma"],
        "nome": "Resma A4",
        "quantidade": 10,
        "estoque_minimo": 4,
        "status": "Disponível",
    }
    assert materiais["Grampeador"]["quantidade"] == 0
    assert materiais["Grampeador"]["status"] == "Indisponível"


def test_ca11_saldos_acompanham_entradas_e_saidas(
    client: TestClient,
) -> None:
    ids = _preparar(client)

    client.post(f"/materiais/{ids['grampeador']}/entrada", json={"quantidade": 4})
    client.post(f"/materiais/{ids['caneta']}/saida", json={"quantidade": 5})

    resumo = _por_categoria(client)
    totais = client.get("/saldos").json()["totais"]
    assert resumo["Papelaria"]["total_unidades"] == 14
    assert resumo["Papelaria"]["total_indisponiveis"] == 0
    assert resumo["Escrita"]["total_unidades"] == 0
    assert resumo["Escrita"]["total_indisponiveis"] == 1
    assert totais == {
        "total_materiais": 3,
        "total_unidades": 14,
        "total_indisponiveis": 1,
    }


def test_ca11_saida_bloqueada_nao_altera_os_saldos(client: TestClient) -> None:
    ids = _preparar(client)
    antes = client.get("/saldos").json()

    bloqueada = client.post(f"/materiais/{ids['caneta']}/saida", json={"quantidade": 6})

    assert bloqueada.status_code == 409
    assert client.get("/saldos").json() == antes


def test_ca11_categorias_e_materiais_em_ordem_alfabetica_sem_diferenciar_caixa(
    client: TestClient,
) -> None:
    client.post("/categorias", json={"nome": "livros"})
    _cadastrar(client, "zebra", "Escrita", 1)
    _cadastrar(client, "Abacate", "Escrita", 1)
    _cadastrar(client, "caderno", "Escrita", 1)

    corpo = client.get("/saldos").json()

    assert [c["categoria"]["nome"] for c in corpo["categorias"]] == [
        "Escrita",
        "Informática",
        "livros",
        "Papelaria",
    ]
    escrita = next(
        c for c in corpo["categorias"] if c["categoria"]["nome"] == "Escrita"
    )
    assert [m["nome"] for m in escrita["materiais"]] == ["Abacate", "caderno", "zebra"]


def test_ca11_sem_materiais_todos_os_totais_sao_zero(client: TestClient) -> None:
    corpo = client.get("/saldos").json()

    assert corpo["totais"] == {
        "total_materiais": 0,
        "total_unidades": 0,
        "total_indisponiveis": 0,
    }
    assert [c["categoria"]["nome"] for c in corpo["categorias"]] == [
        "Escrita",
        "Informática",
        "Papelaria",
    ]


def test_ca11_renomear_categoria_aparece_nos_saldos(
    client: TestClient, criar_material: Callable[..., int]
) -> None:
    criar_material("Caneta", quantidade=2)
    primeira = client.get("/categorias").json()[0]

    client.put(
        f"/categorias/{primeira['id']}",
        json={"nome": "Escritório", "confirmar": True},
    )

    nomes = [c["categoria"]["nome"] for c in client.get("/saldos").json()["categorias"]]
    assert "Escritório" in nomes
    assert primeira["nome"] not in nomes
