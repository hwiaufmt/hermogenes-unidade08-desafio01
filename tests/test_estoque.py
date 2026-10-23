from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Movimentacao


def test_ca05_saldo_zerado_vira_indisponivel_sem_acao_manual(
    client: TestClient, criar_material: Callable[..., int]
) -> None:
    material_id = criar_material(quantidade=3)
    assert client.get(f"/materiais/{material_id}").json()["status"] == "Disponível"

    client.post(f"/materiais/{material_id}/saida", json={"quantidade": 3})

    corpo = client.get(f"/materiais/{material_id}").json()
    assert corpo["quantidade"] == 0
    assert corpo["status"] == "Indisponível"


def test_ca05_nova_entrada_devolve_status_disponivel(
    client: TestClient, criar_material: Callable[..., int]
) -> None:
    material_id = criar_material(quantidade=3)
    client.post(f"/materiais/{material_id}/saida", json={"quantidade": 3})

    resposta = client.post(f"/materiais/{material_id}/entrada", json={"quantidade": 2})

    assert resposta.json()["quantidade"] == 2
    assert resposta.json()["status"] == "Disponível"


def test_ca05_status_aparece_na_listagem(
    client: TestClient, criar_material: Callable[..., int]
) -> None:
    criar_material("Caneta", quantidade=2)
    criar_material("Lápis", quantidade=0)

    status = {m["nome"]: m["status"] for m in client.get("/materiais").json()}

    assert status == {"Caneta": "Disponível", "Lápis": "Indisponível"}


def _cadastrar(client: TestClient, nome: str, categoria: str, quantidade: int) -> None:
    categorias = {c["nome"]: c["id"] for c in client.get("/categorias").json()}
    client.post(
        "/materiais",
        json={
            "nome": nome,
            "categoria_id": categorias[categoria],
            "quantidade": quantidade,
        },
    )


def test_ca06_listagem_traz_categoria_e_saldo_de_cada_material(
    client: TestClient,
) -> None:
    _cadastrar(client, "Resma A4", "Papelaria", 10)
    _cadastrar(client, "Caneta", "Escrita", 0)
    _cadastrar(client, "Grampeador", "Papelaria", 2)

    materiais = client.get("/materiais").json()

    por_categoria: dict[str, dict[str, int]] = {}
    for m in materiais:
        por_categoria.setdefault(m["categoria"]["nome"], {})[m["nome"]] = m[
            "quantidade"
        ]
    assert por_categoria == {
        "Papelaria": {"Resma A4": 10, "Grampeador": 2},
        "Escrita": {"Caneta": 0},
    }


def test_ca06_filtro_lista_somente_a_categoria_escolhida(client: TestClient) -> None:
    _cadastrar(client, "Resma A4", "Papelaria", 10)
    _cadastrar(client, "Caneta", "Escrita", 5)
    escrita = next(
        c["id"] for c in client.get("/categorias").json() if c["nome"] == "Escrita"
    )

    materiais = client.get("/materiais", params={"categoria_id": escrita}).json()

    assert [m["nome"] for m in materiais] == ["Caneta"]


def test_ca06_categoria_sem_material_retorna_lista_vazia(client: TestClient) -> None:
    _cadastrar(client, "Resma A4", "Papelaria", 10)
    informatica = next(
        c["id"] for c in client.get("/categorias").json() if c["nome"] == "Informática"
    )

    resposta = client.get("/materiais", params={"categoria_id": informatica})

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_ca06_pagina_estoque_tem_filtro_de_categoria(client: TestClient) -> None:
    html = client.get("/").text

    assert 'for="filtro-categoria"' in html
    assert 'id="grupos"' in html


def test_movimentacoes_registram_tipo_quantidade_e_saldo_apos(
    client: TestClient,
    criar_material: Callable[..., int],
    fabrica_sessao: sessionmaker[Session],
) -> None:
    material_id = criar_material(quantidade=5)

    client.post(f"/materiais/{material_id}/entrada", json={"quantidade": 3})
    client.post(f"/materiais/{material_id}/saida", json={"quantidade": 8})

    with fabrica_sessao() as db:
        registros = db.scalars(select(Movimentacao).order_by(Movimentacao.id)).all()
        resumo = [(r.tipo, r.quantidade, r.saldo_apos) for r in registros]
        assert resumo == [("entrada", 3, 8), ("saida", 8, 0)]
        assert all(r.data is not None for r in registros)
