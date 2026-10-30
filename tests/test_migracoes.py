"""Migração leve: acrescenta a coluna da exclusão lógica a um banco antigo."""

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.migracoes import migrar
from app.models import Material

TABELAS_ANTIGAS = (
    "CREATE TABLE categorias (id INTEGER PRIMARY KEY, nome VARCHAR(100) UNIQUE)",
    """CREATE TABLE materiais (
        id INTEGER PRIMARY KEY,
        nome VARCHAR(150) NOT NULL,
        categoria_id INTEGER NOT NULL REFERENCES categorias (id),
        quantidade INTEGER NOT NULL DEFAULT 0,
        estoque_minimo INTEGER NOT NULL DEFAULT 0,
        CONSTRAINT ck_material_quantidade CHECK (quantidade >= 0),
        CONSTRAINT ck_material_estoque_minimo CHECK (estoque_minimo >= 0)
    )""",
)


@pytest.fixture
def banco_antigo() -> Engine:
    """Banco no formato anterior à exclusão lógica, com dados já gravados."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    with engine.begin() as conexao:
        for comando in TABELAS_ANTIGAS:
            conexao.execute(text(comando))
        conexao.execute(
            text("INSERT INTO categorias (id, nome) VALUES (1, 'Lapiseira')")
        )
        conexao.execute(
            text(
                "INSERT INTO materiais "
                "(id, nome, categoria_id, quantidade, estoque_minimo) "
                "VALUES (1, 'pentel', 1, 8, 5)"
            )
        )
    return engine


COLUNAS_ACRESCENTADAS = ["materiais.excluido_em", "categorias.excluido_em"]


def _colunas(engine: Engine, tabela: str = "materiais") -> set[str]:
    return {c["name"] for c in inspect(engine).get_columns(tabela)}


def test_banco_antigo_nao_tem_a_coluna_e_a_migracao_a_cria(
    banco_antigo: Engine,
) -> None:
    assert "excluido_em" not in _colunas(banco_antigo)
    assert "excluido_em" not in _colunas(banco_antigo, "categorias")

    aplicadas = migrar(banco_antigo)

    assert aplicadas == COLUNAS_ACRESCENTADAS
    assert "excluido_em" in _colunas(banco_antigo)
    assert "excluido_em" in _colunas(banco_antigo, "categorias")


def test_migracao_preserva_os_dados_existentes(banco_antigo: Engine) -> None:
    migrar(banco_antigo)

    with banco_antigo.connect() as conexao:
        linha = conexao.execute(
            text(
                "SELECT id, nome, categoria_id, quantidade, estoque_minimo, "
                "excluido_em FROM materiais"
            )
        ).one()
    assert tuple(linha) == (1, "pentel", 1, 8, 5, None)


def test_material_antigo_continua_ativo_e_legivel_pelo_modelo(
    banco_antigo: Engine,
) -> None:
    migrar(banco_antigo)

    with sessionmaker(bind=banco_antigo)() as db:
        material = db.scalar(select(Material).where(Material.excluido_em.is_(None)))
        assert material is not None
        assert (material.nome, material.quantidade) == ("pentel", 8)


def test_migracao_e_idempotente(banco_antigo: Engine) -> None:
    primeira = migrar(banco_antigo)
    segunda = migrar(banco_antigo)

    assert primeira == COLUNAS_ACRESCENTADAS
    assert segunda == []
    assert "excluido_em" in _colunas(banco_antigo)


def test_banco_novo_ja_nasce_com_a_coluna_e_a_migracao_nao_faz_nada() -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)

    assert "excluido_em" in _colunas(engine)
    assert "excluido_em" in _colunas(engine, "categorias")
    assert migrar(engine) == []


def test_migracao_preserva_a_categoria_existente_e_ela_continua_ativa(
    banco_antigo: Engine,
) -> None:
    from app.services.estoque import listar_categorias

    migrar(banco_antigo)

    with sessionmaker(bind=banco_antigo)() as db:
        assert [c.nome for c in listar_categorias(db)] == ["Lapiseira"]


def test_exclusao_logica_funciona_em_banco_migrado(banco_antigo: Engine) -> None:
    from app.services.estoque import excluir_material, listar_materiais

    migrar(banco_antigo)

    with sessionmaker(bind=banco_antigo, expire_on_commit=False)() as db:
        excluir_material(db, 1, confirmar=True)
        assert listar_materiais(db) == []

    with banco_antigo.connect() as conexao:
        linha = conexao.execute(
            text("SELECT nome, excluido_em FROM materiais WHERE id = 1")
        ).one()
    assert linha[0] == "pentel"
    assert linha[1] is not None
