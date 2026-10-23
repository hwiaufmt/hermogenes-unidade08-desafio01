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
