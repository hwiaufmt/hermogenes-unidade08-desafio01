from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Material, Movimentacao


def _id_categoria(client: TestClient, nome: str) -> int:
    return next(c["id"] for c in client.get("/categorias").json() if c["nome"] == nome)


def _cadastrar(
    client: TestClient, nome: str, categoria: str = "Escrita", quantidade: int = 0
) -> int:
    resposta = client.post(
        "/materiais",
        json={
            "nome": nome,
            "categoria_id": _id_categoria(client, categoria),
            "quantidade": quantidade,
        },
    )
    assert resposta.status_code == 201
    return resposta.json()["id"]


def _nomes_listados(client: TestClient) -> list[str]:
    return [m["nome"] for m in client.get("/materiais").json()]


def test_ca12_exclui_material_sem_saldo_direto(client: TestClient) -> None:
    material_id = _cadastrar(client, "Caneta", quantidade=0)

    resposta = client.delete(f"/materiais/{material_id}")

    assert resposta.status_code == 204
    assert resposta.content == b""


def test_ca12_material_excluido_deixa_de_aparecer_e_de_ser_consultado(
    client: TestClient,
) -> None:
    excluido = _cadastrar(client, "Caneta")
    _cadastrar(client, "Lápis")

    client.delete(f"/materiais/{excluido}")

    assert _nomes_listados(client) == ["Lápis"]
    assert client.get(f"/materiais/{excluido}").status_code == 404
    assert client.get("/materiais", params={"q": "caneta"}).json() == []
    indisponiveis = client.get("/materiais", params={"status": "Indisponível"}).json()
    assert [m["nome"] for m in indisponiveis] == ["Lápis"]


def test_ca12_material_excluido_nao_aceita_movimentacao(
    client: TestClient, contar_movimentacoes: Callable[[], int]
) -> None:
    material_id = _cadastrar(client, "Caneta", quantidade=0)
    client.delete(f"/materiais/{material_id}")
    antes = contar_movimentacoes()

    entrada = client.post(f"/materiais/{material_id}/entrada", json={"quantidade": 1})
    saida = client.post(f"/materiais/{material_id}/saida", json={"quantidade": 1})

    assert entrada.status_code == 404
    assert saida.status_code == 404
    assert contar_movimentacoes() == antes


def test_ca12_registro_nao_e_apagado_do_banco(
    client: TestClient, fabrica_sessao: sessionmaker[Session]
) -> None:
    material_id = _cadastrar(client, "Caneta", quantidade=0)

    client.delete(f"/materiais/{material_id}")

    with fabrica_sessao() as db:
        material = db.get(Material, material_id)
        assert material is not None
        assert material.nome == "Caneta"
        assert material.excluido_em is not None


def test_ca12_movimentacoes_antigas_continuam_guardadas(
    client: TestClient, fabrica_sessao: sessionmaker[Session]
) -> None:
    material_id = _cadastrar(client, "Caneta", quantidade=5)
    client.post(f"/materiais/{material_id}/entrada", json={"quantidade": 3})
    client.post(f"/materiais/{material_id}/saida", json={"quantidade": 8})

    client.delete(f"/materiais/{material_id}")  # saldo 0: exclui direto

    with fabrica_sessao() as db:
        registros = db.scalars(
            select(Movimentacao).where(Movimentacao.material_id == material_id)
        ).all()
        assert [(r.tipo, r.quantidade, r.saldo_apos) for r in registros] == [
            ("entrada", 3, 8),
            ("saida", 8, 0),
        ]


def test_ca12_com_saldo_sem_confirmacao_informa_o_saldo_e_nao_exclui(
    client: TestClient,
) -> None:
    material_id = _cadastrar(client, "Resma A4", "Papelaria", quantidade=8)

    resposta = client.delete(f"/materiais/{material_id}")

    assert resposta.status_code == 409
    assert resposta.json() == {
        "detail": (
            "O material 'Resma A4' tem 8 unidades em estoque; ao excluir, ele deixa "
            "de aparecer no sistema. Confirme para excluir."
        ),
        "saldo": 8,
    }
    assert client.get(f"/materiais/{material_id}").status_code == 200
    assert "Resma A4" in _nomes_listados(client)


def test_ca12_saldo_de_uma_unidade_usa_o_singular(client: TestClient) -> None:
    material_id = _cadastrar(client, "Régua", quantidade=1)

    resposta = client.delete(f"/materiais/{material_id}")

    assert resposta.status_code == 409
    assert "tem 1 unidade em estoque" in resposta.json()["detail"]
    assert resposta.json()["saldo"] == 1


def test_ca12_com_saldo_e_confirmacao_exclui(client: TestClient) -> None:
    material_id = _cadastrar(client, "Resma A4", "Papelaria", quantidade=8)

    resposta = client.delete(f"/materiais/{material_id}", params={"confirmar": "true"})

    assert resposta.status_code == 204
    assert client.get(f"/materiais/{material_id}").status_code == 404


def test_ca12_depois_de_zerar_o_saldo_exclui_sem_confirmacao(
    client: TestClient,
) -> None:
    material_id = _cadastrar(client, "Caneta", quantidade=2)
    assert client.delete(f"/materiais/{material_id}").status_code == 409
    client.post(f"/materiais/{material_id}/saida", json={"quantidade": 2})

    assert client.delete(f"/materiais/{material_id}").status_code == 204


def test_ca12_material_inexistente_ou_ja_excluido_retorna_404(
    client: TestClient,
) -> None:
    material_id = _cadastrar(client, "Caneta")
    client.delete(f"/materiais/{material_id}")

    ja_excluido = client.delete(f"/materiais/{material_id}")
    inexistente = client.delete("/materiais/999")

    assert ja_excluido.status_code == 404
    assert inexistente.status_code == 404
    assert inexistente.json()["detail"] == "O material 999 não existe."


def test_ca12_confirmacao_invalida_devolve_mensagem_em_portugues(
    client: TestClient,
) -> None:
    material_id = _cadastrar(client, "Caneta")

    resposta = client.delete(
        f"/materiais/{material_id}", params={"confirmar": "talvez"}
    )

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "Valor inválido no campo 'confirmar'."


def test_ca12_excluidos_saem_dos_saldos_e_dos_totais(client: TestClient) -> None:
    _cadastrar(client, "Caneta", "Escrita", quantidade=5)
    excluido = _cadastrar(client, "Lápis", "Escrita", quantidade=0)
    _cadastrar(client, "Resma A4", "Papelaria", quantidade=10)

    client.delete(f"/materiais/{excluido}")

    corpo = client.get("/saldos").json()
    escrita = next(
        c for c in corpo["categorias"] if c["categoria"]["nome"] == "Escrita"
    )
    assert [m["nome"] for m in escrita["materiais"]] == ["Caneta"]
    assert escrita["total_materiais"] == 1
    assert escrita["total_indisponiveis"] == 0
    assert corpo["totais"] == {
        "total_materiais": 2,
        "total_unidades": 15,
        "total_indisponiveis": 0,
    }


def test_ca12_excluidos_nao_contam_nos_totais_da_categoria(client: TestClient) -> None:
    _cadastrar(client, "Caneta", "Escrita")
    excluido = _cadastrar(client, "Lápis", "Escrita")
    client.delete(f"/materiais/{excluido}")

    totais = {c["nome"]: c["total_materiais"] for c in client.get("/categorias").json()}

    assert totais["Escrita"] == 1


def test_ca12_aviso_de_edicao_de_categoria_conta_so_materiais_ativos(
    client: TestClient,
) -> None:
    escrita = _id_categoria(client, "Escrita")
    material_id = _cadastrar(client, "Caneta", "Escrita")
    client.delete(f"/materiais/{material_id}")

    sem_aviso = client.put(f"/categorias/{escrita}", json={"nome": "Escritório"})

    assert sem_aviso.status_code == 200
    assert sem_aviso.json()["total_materiais"] == 0


def test_ca12_aviso_de_edicao_ignora_excluidos_mas_conta_os_ativos(
    client: TestClient,
) -> None:
    escrita = _id_categoria(client, "Escrita")
    excluido = _cadastrar(client, "Caneta", "Escrita")
    _cadastrar(client, "Lápis", "Escrita")
    _cadastrar(client, "Borracha", "Escrita")
    client.delete(f"/materiais/{excluido}")

    resposta = client.put(f"/categorias/{escrita}", json={"nome": "Escritório"})

    assert resposta.status_code == 409
    assert resposta.json()["afetados"] == 2


def test_ca12_pode_cadastrar_outro_material_com_o_nome_de_um_excluido(
    client: TestClient,
) -> None:
    material_id = _cadastrar(client, "Caneta")
    client.delete(f"/materiais/{material_id}")

    novo = _cadastrar(client, "Caneta", quantidade=4)

    assert novo != material_id
    assert _nomes_listados(client) == ["Caneta"]
    assert client.get(f"/materiais/{novo}").json()["quantidade"] == 4


def test_ca12_exclusao_nao_mexe_nos_outros_materiais(
    client: TestClient, fabrica_sessao: sessionmaker[Session]
) -> None:
    excluido = _cadastrar(client, "Caneta", quantidade=0)
    _cadastrar(client, "Lápis", quantidade=3)

    client.delete(f"/materiais/{excluido}")

    with fabrica_sessao() as db:
        total = db.scalar(select(func.count()).select_from(Material))
        ativos = db.scalar(
            select(func.count())
            .select_from(Material)
            .where(Material.excluido_em.is_(None))
        )
    assert (total, ativos) == (2, 1)
