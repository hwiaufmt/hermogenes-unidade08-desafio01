import os

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app import config
from app.main import _criar_administrador_inicial
from app.services.usuarios import (
    PERFIL_ADMINISTRADOR,
    PERFIL_OPERADOR,
    autenticar,
    criar_administrador_inicial,
    criar_usuario,
    listar_usuarios,
)

CPF = "529.982.247-25"
SENHA = "senha-segura-1"


def _criar(db: Session):
    return criar_administrador_inicial(
        db, CPF, SENHA, "Administrador", "administrador@estoque.local"
    )


def test_cria_o_primeiro_administrador_quando_nao_ha_usuarios(
    fabrica_sessao: sessionmaker[Session],
) -> None:
    with fabrica_sessao() as db:
        admin = _criar(db)

        assert admin is not None
        assert admin.perfil == PERFIL_ADMINISTRADOR
        assert admin.cpf == "52998224725"
        assert admin.ativo is True
        assert autenticar(db, CPF, SENHA).id == admin.id


def test_nao_cria_administrador_se_ja_existe_algum_usuario(
    fabrica_sessao: sessionmaker[Session],
) -> None:
    with fabrica_sessao() as db:
        criar_usuario(
            db, "Maria", "11144477735", "m@exemplo.com", PERFIL_OPERADOR, SENHA
        )

        assert _criar(db) is None
        assert len(listar_usuarios(db)) == 1


def test_administrador_inicial_e_criado_uma_unica_vez(
    fabrica_sessao: sessionmaker[Session],
) -> None:
    with fabrica_sessao() as db:
        _criar(db)

        assert _criar(db) is None
        assert len(listar_usuarios(db)) == 1


def test_rejeita_cpf_invalido_no_administrador_inicial(
    fabrica_sessao: sessionmaker[Session],
) -> None:
    with fabrica_sessao() as db, pytest.raises(ValueError, match="CPF"):
        criar_administrador_inicial(
            db, "11111111111", SENHA, "Administrador", "a@estoque.local"
        )


def test_rejeita_senha_curta_no_administrador_inicial(
    fabrica_sessao: sessionmaker[Session],
) -> None:
    with fabrica_sessao() as db, pytest.raises(ValueError, match="senha"):
        criar_administrador_inicial(
            db, CPF, "curta", "Administrador", "a@estoque.local"
        )


def test_inicio_do_app_cria_o_administrador_padrao_em_banco_vazio(
    fabrica_sessao: sessionmaker[Session],
) -> None:
    with fabrica_sessao() as db:
        _criar_administrador_inicial(db)

        usuarios = listar_usuarios(db)
        assert len(usuarios) == 1
        assert usuarios[0].perfil == PERFIL_ADMINISTRADOR
        assert autenticar(db, config.ADMIN_CPF, config.ADMIN_SENHA).id == usuarios[0].id

        _criar_administrador_inicial(db)  # segundo início: não duplica
        assert len(listar_usuarios(db)) == 1


@pytest.mark.skipif(
    bool(os.environ.get("ESTOQUE_ADMIN_CPF") or os.environ.get("ESTOQUE_ADMIN_SENHA")),
    reason="variáveis do administrador definidas neste ambiente",
)
def test_administrador_padrao_do_prototipo_usa_a_senha_123456() -> None:
    assert config.ADMIN_CPF == "529.982.247-25"
    assert config.ADMIN_SENHA == config.SENHA_PADRAO == "123456"
