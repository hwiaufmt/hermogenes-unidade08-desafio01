from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Categoria
from app.services.estoque import semear_categorias


def _id_categoria(client: TestClient, nome: str) -> int:
    return next(c["id"] for c in client.get("/categorias").json() if c["nome"] == nome)


def _nomes_listados(client: TestClient) -> list[str]:
    return [c["nome"] for c in client.get("/categorias").json()]


def _criar_categoria(client: TestClient, nome: str) -> int:
    resposta = client.post("/categorias", json={"nome": nome})
    assert resposta.status_code == 201
    return resposta.json()["id"]


def _cadastrar_material(client: TestClient, categoria_id: int, nome: str) -> int:
    resposta = client.post(
        "/materiais", json={"nome": nome, "categoria_id": categoria_id}
    )
    assert resposta.status_code == 201
    return resposta.json()["id"]


def test_ca15_exclui_categoria_sem_materiais(client: TestClient) -> None:
    limpeza = _criar_categoria(client, "Limpeza")

    resposta = client.delete(f"/categorias/{limpeza}")

    assert resposta.status_code == 204
    assert resposta.content == b""


def test_ca15_categoria_excluida_some_da_lista_dos_saldos_e_do_cadastro(
    client: TestClient,
) -> None:
    limpeza = _criar_categoria(client, "Limpeza")

    client.delete(f"/categorias/{limpeza}")

    assert "Limpeza" not in _nomes_listados(client)
    saldos = client.get("/saldos").json()["categorias"]
    assert "Limpeza" not in [s["categoria"]["nome"] for s in saldos]
    cadastro = client.post(
        "/materiais", json={"nome": "Sabão", "categoria_id": limpeza}
    )
    assert cadastro.status_code == 422


def test_ca15_categoria_excluida_responde_404_em_filtro_edicao_e_nova_exclusao(
    client: TestClient,
) -> None:
    limpeza = _criar_categoria(client, "Limpeza")
    client.delete(f"/categorias/{limpeza}")

    filtro = client.get("/materiais", params={"categoria_id": limpeza})
    edicao = client.put(f"/categorias/{limpeza}", json={"nome": "Outra"})
    de_novo = client.delete(f"/categorias/{limpeza}")

    assert filtro.status_code == 404
    assert edicao.status_code == 404
    assert de_novo.status_code == 404


def test_ca15_categoria_inexistente_responde_404(client: TestClient) -> None:
    resposta = client.delete("/categorias/9999")

    assert resposta.status_code == 404
    assert "9999" in resposta.json()["detail"]


def test_ca15_categoria_com_materiais_e_bloqueada_e_nada_e_gravado(
    client: TestClient,
) -> None:
    escrita = _id_categoria(client, "Escrita")
    _cadastrar_material(client, escrita, "Caneta")
    _cadastrar_material(client, escrita, "Lápis")

    resposta = client.delete(f"/categorias/{escrita}")

    assert resposta.status_code == 409
    assert resposta.json()["materiais"] == 2
    assert "2 materiais" in resposta.json()["detail"]
    assert "Escrita" in _nomes_listados(client)
    assert len(client.get("/materiais").json()) == 2


def test_ca15_mensagem_no_singular_com_um_material(client: TestClient) -> None:
    escrita = _id_categoria(client, "Escrita")
    _cadastrar_material(client, escrita, "Caneta")

    resposta = client.delete(f"/categorias/{escrita}")

    assert resposta.json()["materiais"] == 1
    assert "1 material;" in resposta.json()["detail"]


def test_ca15_material_ja_excluido_nao_bloqueia_a_exclusao_da_categoria(
    client: TestClient,
) -> None:
    limpeza = _criar_categoria(client, "Limpeza")
    material = _cadastrar_material(client, limpeza, "Sabão")
    client.delete(f"/materiais/{material}")

    resposta = client.delete(f"/categorias/{limpeza}")

    assert resposta.status_code == 204


def test_ca15_o_registro_continua_no_banco_com_data_e_nome_marcado(
    client: TestClient, fabrica_sessao: sessionmaker[Session]
) -> None:
    limpeza = _criar_categoria(client, "Limpeza")

    client.delete(f"/categorias/{limpeza}")

    with fabrica_sessao() as db:
        categoria = db.get(Categoria, limpeza)
        assert categoria is not None
        assert categoria.excluido_em is not None
        assert categoria.nome == f"Limpeza [excluída #{limpeza}]"


def test_ca15_nome_de_categoria_excluida_pode_ser_reutilizado(
    client: TestClient,
) -> None:
    antiga = _criar_categoria(client, "Limpeza")
    client.delete(f"/categorias/{antiga}")

    nova = client.post("/categorias", json={"nome": "limpeza"})

    assert nova.status_code == 201
    assert nova.json()["id"] != antiga
    assert _nomes_listados(client).count("limpeza") == 1


def test_ca15_reutilizar_o_nome_duas_vezes_nao_colide_no_banco(
    client: TestClient,
) -> None:
    for _ in range(2):
        categoria = _criar_categoria(client, "Limpeza")
        assert client.delete(f"/categorias/{categoria}").status_code == 204

    assert _criar_categoria(client, "Limpeza")


def test_ca15_nome_repetido_entre_ativas_continua_recusado(
    client: TestClient,
) -> None:
    resposta = client.post("/categorias", json={"nome": "ESCRITA"})

    assert resposta.status_code == 422


def test_ca15_categoria_excluida_nao_conta_como_nome_repetido_na_edicao(
    client: TestClient,
) -> None:
    antiga = _criar_categoria(client, "Limpeza")
    client.delete(f"/categorias/{antiga}")
    outra = _criar_categoria(client, "Higiene")

    resposta = client.put(f"/categorias/{outra}", json={"nome": "Limpeza"})

    assert resposta.status_code == 200


def test_ca15_seed_nao_recria_categoria_do_seed_excluida(
    client: TestClient, fabrica_sessao: sessionmaker[Session]
) -> None:
    informatica = _id_categoria(client, "Informática")
    assert client.delete(f"/categorias/{informatica}").status_code == 204

    with fabrica_sessao() as db:
        semear_categorias(db)

    assert _nomes_listados(client) == ["Escrita", "Papelaria"]


def test_ca15_seed_so_cria_as_iniciais_com_a_tabela_vazia(
    fabrica_sessao: sessionmaker[Session],
) -> None:
    with fabrica_sessao() as db:
        for categoria in db.scalars(select(Categoria)):
            db.delete(categoria)
        db.commit()

        semear_categorias(db)
        semear_categorias(db)

        nomes = sorted(c.nome for c in db.scalars(select(Categoria)))
        assert nomes == ["Escrita", "Informática", "Papelaria"]
