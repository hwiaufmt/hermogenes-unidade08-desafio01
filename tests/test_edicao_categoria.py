from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient


def _id(client: TestClient, nome: str) -> int:
    return next(c["id"] for c in client.get("/categorias").json() if c["nome"] == nome)


def _cadastrar(client: TestClient, nome: str, categoria: str) -> None:
    resposta = client.post(
        "/materiais",
        json={"nome": nome, "categoria_id": _id(client, categoria), "quantidade": 1},
    )
    assert resposta.status_code == 201


def _nomes_das_categorias(client: TestClient) -> list[str]:
    return [c["nome"] for c in client.get("/categorias").json()]


def _criar_categoria_vazia(client: TestClient, nome: str = "Limpeza") -> int:
    return client.post("/categorias", json={"nome": nome}).json()["id"]


# ---------------------------------------------------------------- CA-09


def test_ca09_renomeia_categoria_sem_materiais(client: TestClient) -> None:
    categoria_id = _criar_categoria_vazia(client)

    resposta = client.put(f"/categorias/{categoria_id}", json={"nome": "Higiene"})

    assert resposta.status_code == 200
    assert resposta.json() == {
        "id": categoria_id,
        "nome": "Higiene",
        "total_materiais": 0,
    }
    nomes = _nomes_das_categorias(client)
    assert "Higiene" in nomes
    assert "Limpeza" not in nomes


def test_ca09_nome_e_aparado(client: TestClient) -> None:
    categoria_id = _criar_categoria_vazia(client)

    resposta = client.put(f"/categorias/{categoria_id}", json={"nome": "  Higiene  "})

    assert resposta.json()["nome"] == "Higiene"


@pytest.mark.parametrize("nome", ["", "   "])
def test_ca09_nome_vazio_retorna_422_e_nao_grava(client: TestClient, nome: str) -> None:
    categoria_id = _criar_categoria_vazia(client)

    resposta = client.put(f"/categorias/{categoria_id}", json={"nome": nome})

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "O nome da categoria é obrigatório."
    assert "Limpeza" in _nomes_das_categorias(client)


def test_ca09_nome_de_outra_categoria_retorna_422_e_nao_grava(
    client: TestClient,
) -> None:
    categoria_id = _criar_categoria_vazia(client)

    resposta = client.put(f"/categorias/{categoria_id}", json={"nome": "Papelaria"})

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "Já existe uma categoria chamada 'Papelaria'."
    assert "Limpeza" in _nomes_das_categorias(client)


def test_ca09_categoria_inexistente_retorna_404(client: TestClient) -> None:
    resposta = client.put("/categorias/999", json={"nome": "Qualquer"})

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "A categoria 999 não existe."


def test_ca09_manter_o_mesmo_nome_nao_altera_nem_pede_confirmacao(
    client: TestClient,
) -> None:
    _cadastrar(client, "Caneta", "Escrita")

    resposta = client.put(
        "/categorias/" + str(_id(client, "Escrita")), json={"nome": "Escrita"}
    )

    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Escrita"
    assert resposta.json()["total_materiais"] == 1


def test_ca09_corpo_sem_nome_devolve_mensagem_em_portugues(
    client: TestClient,
) -> None:
    categoria_id = _criar_categoria_vazia(client)

    resposta = client.put(f"/categorias/{categoria_id}", json={})

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "O campo 'nome' é obrigatório."


# ---------------------------------------------------------------- CA-10


def test_ca10_com_materiais_sem_confirmacao_informa_a_quantidade_e_nao_grava(
    client: TestClient,
) -> None:
    _cadastrar(client, "Caneta azul", "Escrita")
    _cadastrar(client, "Caneta preta", "Escrita")
    _cadastrar(client, "Lápis", "Escrita")
    escrita = _id(client, "Escrita")

    resposta = client.put(f"/categorias/{escrita}", json={"nome": "Escritório"})

    assert resposta.status_code == 409
    corpo = resposta.json()
    assert corpo["afetados"] == 3
    assert corpo["detail"] == (
        "Esta categoria tem 3 materiais; a mudança de nome afetará 3 registros. "
        "Confirme para gravar."
    )
    nomes = _nomes_das_categorias(client)
    assert "Escrita" in nomes
    assert "Escritório" not in nomes


def test_ca10_com_um_unico_material_a_mensagem_fica_no_singular(
    client: TestClient,
) -> None:
    _cadastrar(client, "Caneta", "Escrita")

    resposta = client.put(
        f"/categorias/{_id(client, 'Escrita')}", json={"nome": "Escritório"}
    )

    assert resposta.status_code == 409
    assert resposta.json()["afetados"] == 1
    assert resposta.json()["detail"] == (
        "Esta categoria tem 1 material; a mudança de nome afetará 1 registro. "
        "Confirme para gravar."
    )


def test_ca10_com_confirmacao_grava_e_os_materiais_acompanham_o_novo_nome(
    client: TestClient,
) -> None:
    _cadastrar(client, "Caneta azul", "Escrita")
    _cadastrar(client, "Lápis", "Escrita")
    escrita = _id(client, "Escrita")

    resposta = client.put(
        f"/categorias/{escrita}", json={"nome": "Escritório", "confirmar": True}
    )

    assert resposta.status_code == 200
    assert resposta.json() == {
        "id": escrita,
        "nome": "Escritório",
        "total_materiais": 2,
    }
    materiais = client.get("/materiais", params={"categoria_id": escrita}).json()
    assert [m["nome"] for m in materiais] == ["Caneta azul", "Lápis"]
    assert {m["categoria"]["nome"] for m in materiais} == {"Escritório"}


def test_ca10_categoria_sem_materiais_grava_direto_mesmo_sem_confirmacao(
    client: TestClient,
) -> None:
    categoria_id = _criar_categoria_vazia(client)

    resposta = client.put(f"/categorias/{categoria_id}", json={"nome": "Higiene"})

    assert resposta.status_code == 200


def test_ca10_confirmar_em_categoria_sem_materiais_tambem_e_aceito(
    client: TestClient,
) -> None:
    categoria_id = _criar_categoria_vazia(client)

    resposta = client.put(
        f"/categorias/{categoria_id}", json={"nome": "Higiene", "confirmar": True}
    )

    assert resposta.status_code == 200


def test_ca10_so_conta_os_materiais_da_propria_categoria(
    client: TestClient,
) -> None:
    _cadastrar(client, "Caneta", "Escrita")
    _cadastrar(client, "Resma A4", "Papelaria")
    _cadastrar(client, "Grampeador", "Papelaria")

    resposta = client.put(
        f"/categorias/{_id(client, 'Papelaria')}", json={"nome": "Escritório"}
    )

    assert resposta.status_code == 409
    assert resposta.json()["afetados"] == 2


def test_ca10_nome_repetido_e_recusado_antes_de_pedir_confirmacao(
    client: TestClient,
) -> None:
    _cadastrar(client, "Caneta", "Escrita")

    resposta = client.put(
        f"/categorias/{_id(client, 'Escrita')}", json={"nome": "Papelaria"}
    )

    assert resposta.status_code == 422
    assert "afetados" not in resposta.json()


def test_ca10_confirmacao_invalida_devolve_mensagem_em_portugues(
    client: TestClient,
) -> None:
    resposta = client.put(
        f"/categorias/{_id(client, 'Escrita')}",
        json={"nome": "Escritório", "confirmar": "talvez"},
    )

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "Valor inválido no campo 'confirmar'."


# ----------------------------------------------- lista com totais de materiais


def test_lista_de_categorias_informa_quantos_materiais_cada_uma_tem(
    client: TestClient, criar_material: Callable[..., int]
) -> None:
    _cadastrar(client, "Caneta", "Escrita")
    _cadastrar(client, "Lápis", "Escrita")
    _cadastrar(client, "Resma A4", "Papelaria")

    totais = {c["nome"]: c["total_materiais"] for c in client.get("/categorias").json()}

    assert totais == {"Escrita": 2, "Informática": 0, "Papelaria": 1}


def test_criar_categoria_continua_devolvendo_id_e_nome(client: TestClient) -> None:
    resposta = client.post("/categorias", json={"nome": "Limpeza"})

    assert resposta.status_code == 201
    assert set(resposta.json()) == {"id", "nome"}
