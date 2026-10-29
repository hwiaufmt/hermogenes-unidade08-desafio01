"""Acesso por perfil usando a matriz de permissões real (sem substituí-la)."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app import permissoes
from app.models import Usuario
from app.permissoes import Acao
from app.services.usuarios import (
    PERFIL_ADMINISTRADOR,
    PERFIL_ESTOQUISTA,
    PERFIL_OPERADOR,
    PERFIS,
    atualizar_usuario,
    inativar_usuario,
)
from tests.conftest import CPFS_DE_TESTE

ADMIN = PERFIL_ADMINISTRADOR
ESTOQUISTA = PERFIL_ESTOQUISTA
OPERADOR = PERFIL_OPERADOR

NOVO_MATERIAL = {"nome": "Caneta", "categoria_id": 1, "quantidade": 3}
NOVO_USUARIO = {
    "nome": "Pessoa Nova",
    "cpf": "52998224725",
    "email": "nova@exemplo.com",
    "perfil": "operador",
    "senha": "senha-segura-1",
}
EDICAO_USUARIO = {"nome": "Editado", "email": "e@exemplo.com", "perfil": "operador"}

# (método, caminho, corpo, perfis autorizados)
ROTAS = [
    ("GET", "/categorias", None, {ESTOQUISTA, OPERADOR}),
    ("POST", "/categorias", {"nome": "Limpeza"}, {ESTOQUISTA}),
    ("PUT", "/categorias/1", {"nome": "Outro nome"}, {ESTOQUISTA}),
    ("GET", "/materiais", None, {ESTOQUISTA, OPERADOR}),
    ("GET", "/materiais/1", None, {ESTOQUISTA, OPERADOR}),
    ("POST", "/materiais", NOVO_MATERIAL, {ESTOQUISTA}),
    ("POST", "/materiais/1/entrada", {"quantidade": 1}, {OPERADOR}),
    ("POST", "/materiais/1/saida", {"quantidade": 1}, {OPERADOR}),
    ("GET", "/usuarios", None, {ADMIN}),
    ("GET", "/usuarios/1", None, {ADMIN}),
    ("POST", "/usuarios", NOVO_USUARIO, {ADMIN}),
    ("PUT", "/usuarios/1", EDICAO_USUARIO, {ADMIN}),
    ("POST", "/usuarios/1/inativar", None, {ADMIN}),
    ("POST", "/usuarios/1/reativar", None, {ADMIN}),
]
IDS_ROTAS = [f"{metodo} {caminho}" for metodo, caminho, _, _ in ROTAS]


def _chamar(client: TestClient, metodo: str, caminho: str, corpo: dict | None):
    return client.request(metodo, caminho, json=corpo)


def _usuario_de_teste(db: Session, perfil: str) -> Usuario:
    return db.scalar(select(Usuario).where(Usuario.cpf == CPFS_DE_TESTE[perfil]))


def test_ca08_matriz_oficial_segue_as_regras_de_negocio() -> None:
    assert permissoes.PERMISSOES == {
        ADMIN: {Acao.GERIR_USUARIOS},
        ESTOQUISTA: {
            Acao.CRIAR_CATEGORIA,
            Acao.EDITAR_CATEGORIA,
            Acao.CADASTRAR_MATERIAL,
            Acao.CONSULTAR_ESTOQUE,
        },
        OPERADOR: {Acao.MOVIMENTAR, Acao.CONSULTAR_ESTOQUE},
    }
    assert set(permissoes.PERMISSOES) == set(PERFIS)


@pytest.mark.parametrize(("metodo", "caminho", "corpo", "perfis"), ROTAS, ids=IDS_ROTAS)
def test_ca08_sem_login_toda_rota_protegida_retorna_401(
    cliente_anonimo: TestClient,
    metodo: str,
    caminho: str,
    corpo: dict | None,
    perfis: set[str],
) -> None:
    resposta = _chamar(cliente_anonimo, metodo, caminho, corpo)

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "É necessário entrar no sistema."


@pytest.mark.parametrize("perfil", sorted(PERFIS))
@pytest.mark.parametrize(("metodo", "caminho", "corpo", "perfis"), ROTAS, ids=IDS_ROTAS)
def test_ca08_cada_perfil_acessa_somente_o_que_lhe_cabe(
    entrar_como: Callable[[str], TestClient],
    perfil: str,
    metodo: str,
    caminho: str,
    corpo: dict | None,
    perfis: set[str],
) -> None:
    client = entrar_como(perfil)

    resposta = _chamar(client, metodo, caminho, corpo)

    if perfil in perfis:
        assert resposta.status_code not in (401, 403), resposta.text
    else:
        assert resposta.status_code == 403
        assert (
            resposta.json()["detail"]
            == "Você não tem permissão para realizar esta ação."
        )


def test_ca08_estoquista_cria_categoria_e_cadastra_material_mas_nao_movimenta(
    entrar_como: Callable[[str], TestClient],
) -> None:
    client = entrar_como(ESTOQUISTA)

    categoria = client.post("/categorias", json={"nome": "Limpeza"})
    material = client.post(
        "/materiais",
        json={
            "nome": "Detergente",
            "categoria_id": categoria.json()["id"],
            "quantidade": 5,
            "estoque_minimo": 2,
        },
    )
    consulta = client.get("/materiais")
    entrada = client.post(
        f"/materiais/{material.json()['id']}/entrada", json={"quantidade": 1}
    )

    assert categoria.status_code == 201
    assert material.status_code == 201
    assert material.json()["estoque_minimo"] == 2
    assert [m["nome"] for m in consulta.json()] == ["Detergente"]
    assert entrada.status_code == 403


def test_ca08_operador_movimenta_e_consulta_mas_nao_cadastra(
    entrar_como: Callable[[str], TestClient],
) -> None:
    material_id = (
        entrar_como(ESTOQUISTA).post("/materiais", json=NOVO_MATERIAL).json()["id"]
    )
    client = entrar_como(OPERADOR)

    entrada = client.post(f"/materiais/{material_id}/entrada", json={"quantidade": 2})
    saida = client.post(f"/materiais/{material_id}/saida", json={"quantidade": 4})
    consulta = client.get(f"/materiais/{material_id}")

    assert entrada.status_code == 200
    assert saida.status_code == 200
    assert consulta.json()["quantidade"] == 1
    assert client.post("/materiais", json=NOVO_MATERIAL).status_code == 403
    assert client.post("/categorias", json={"nome": "Nova"}).status_code == 403
    assert client.get("/usuarios").status_code == 403


def test_ca08_administrador_gerencia_usuarios_mas_nao_mexe_no_estoque(
    entrar_como: Callable[[str], TestClient],
) -> None:
    client = entrar_como(ADMIN)

    novo = client.post("/usuarios", json=NOVO_USUARIO)

    assert novo.status_code == 201
    assert client.get("/materiais").status_code == 403
    assert client.post("/materiais", json=NOVO_MATERIAL).status_code == 403
    assert (
        client.post("/materiais/1/entrada", json={"quantidade": 1}).status_code == 403
    )


def test_ca08_mudar_o_perfil_vale_na_proxima_requisicao(
    entrar_como: Callable[[str], TestClient],
    fabrica_sessao: sessionmaker[Session],
) -> None:
    material_id = (
        entrar_como(ESTOQUISTA).post("/materiais", json=NOVO_MATERIAL).json()["id"]
    )
    client = entrar_como(OPERADOR)
    rota = f"/materiais/{material_id}/entrada"
    assert client.post(rota, json={"quantidade": 1}).status_code == 200

    with fabrica_sessao() as db:
        operador = _usuario_de_teste(db, OPERADOR)
        atualizar_usuario(db, operador.id, operador.nome, operador.email, ESTOQUISTA)

    assert client.post(rota, json={"quantidade": 1}).status_code == 403


def test_ca08_usuario_inativado_perde_o_acesso_com_a_sessao_aberta(
    entrar_como: Callable[[str], TestClient],
    fabrica_sessao: sessionmaker[Session],
) -> None:
    client = entrar_como(OPERADOR)
    assert client.get("/materiais").status_code == 200

    with fabrica_sessao() as db:
        inativar_usuario(db, _usuario_de_teste(db, OPERADOR).id)

    resposta = client.get("/materiais")

    assert resposta.status_code == 401
