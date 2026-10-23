from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.models import Usuario
from app.services.usuarios import criar_usuario, inativar_usuario

CPF_A = "52998224725"
CPF_B = "11144477735"
SENHA = "senha-segura-1"


def _criar_usuario(
    fabrica: sessionmaker[Session], cpf: str = CPF_A, perfil: str = "operador"
) -> Usuario:
    with fabrica() as db:
        return criar_usuario(db, "Maria Silva", cpf, "maria@exemplo.com", perfil, SENHA)


def _entrar(client: TestClient, cpf: str = CPF_A, senha: str = SENHA):
    return client.post("/login", json={"cpf": cpf, "senha": senha})


def test_login_com_cpf_e_senha_corretos_abre_sessao(
    cliente_anonimo: TestClient, fabrica_sessao: sessionmaker[Session]
) -> None:
    usuario = _criar_usuario(fabrica_sessao)

    resposta = _entrar(cliente_anonimo)

    assert resposta.status_code == 200
    assert resposta.json()["id"] == usuario.id
    assert "senha" not in resposta.json()
    assert cliente_anonimo.get("/me").json()["cpf"] == CPF_A


def test_login_aceita_cpf_com_mascara(
    cliente_anonimo: TestClient, fabrica_sessao: sessionmaker[Session]
) -> None:
    _criar_usuario(fabrica_sessao)

    assert _entrar(cliente_anonimo, cpf="529.982.247-25").status_code == 200


def test_login_com_senha_errada_e_rejeitado(
    cliente_anonimo: TestClient, fabrica_sessao: sessionmaker[Session]
) -> None:
    _criar_usuario(fabrica_sessao)

    resposta = _entrar(cliente_anonimo, senha="senha-errada-1")

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "CPF ou senha inválidos."
    assert cliente_anonimo.get("/me").status_code == 401


def test_login_nao_revela_se_o_cpf_existe(
    cliente_anonimo: TestClient, fabrica_sessao: sessionmaker[Session]
) -> None:
    _criar_usuario(fabrica_sessao)

    senha_errada = _entrar(cliente_anonimo, senha="senha-errada-1")
    cpf_inexistente = _entrar(cliente_anonimo, cpf=CPF_B)

    assert senha_errada.status_code == cpf_inexistente.status_code == 401
    assert senha_errada.json() == cpf_inexistente.json()


def test_usuario_inativo_nao_consegue_entrar(
    cliente_anonimo: TestClient, fabrica_sessao: sessionmaker[Session]
) -> None:
    usuario = _criar_usuario(fabrica_sessao)
    with fabrica_sessao() as db:
        inativar_usuario(db, usuario.id)

    resposta = _entrar(cliente_anonimo)

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "CPF ou senha inválidos."


def test_me_sem_login_retorna_401(cliente_anonimo: TestClient) -> None:
    resposta = cliente_anonimo.get("/me")

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "É necessário entrar no sistema."


def test_logout_encerra_a_sessao(
    cliente_anonimo: TestClient, fabrica_sessao: sessionmaker[Session]
) -> None:
    _criar_usuario(fabrica_sessao)
    _entrar(cliente_anonimo)

    resposta = cliente_anonimo.post("/logout")

    assert resposta.status_code == 204
    assert cliente_anonimo.get("/me").status_code == 401


def test_inativar_usuario_derruba_a_sessao_em_andamento(
    cliente_anonimo: TestClient, fabrica_sessao: sessionmaker[Session]
) -> None:
    _criar_usuario(fabrica_sessao, cpf=CPF_B, perfil="administrador")
    usuario = _criar_usuario(fabrica_sessao, perfil="administrador")
    _entrar(cliente_anonimo)
    assert cliente_anonimo.get("/me").status_code == 200

    with fabrica_sessao() as db:
        inativar_usuario(db, usuario.id)

    assert cliente_anonimo.get("/me").status_code == 401


def test_cookie_de_sessao_adulterado_e_ignorado(
    cliente_anonimo: TestClient, fabrica_sessao: sessionmaker[Session]
) -> None:
    _criar_usuario(fabrica_sessao)
    _entrar(cliente_anonimo)
    cliente_anonimo.cookies.set("session", "valor-forjado")

    assert cliente_anonimo.get("/me").status_code == 401


def test_cookie_de_sessao_e_httponly_e_samesite(
    cliente_anonimo: TestClient, fabrica_sessao: sessionmaker[Session]
) -> None:
    _criar_usuario(fabrica_sessao)

    cookie = _entrar(cliente_anonimo).headers["set-cookie"].lower()

    assert "httponly" in cookie
    assert "samesite=lax" in cookie


def test_login_sem_senha_devolve_mensagem_em_portugues(
    cliente_anonimo: TestClient,
) -> None:
    resposta = cliente_anonimo.post("/login", json={"cpf": CPF_A})

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "O campo 'senha' é obrigatório."


def test_login_troca_a_sessao_anterior(
    cliente_anonimo: TestClient, fabrica_sessao: sessionmaker[Session]
) -> None:
    primeiro = _criar_usuario(fabrica_sessao, cpf=CPF_A)
    segundo = _criar_usuario(fabrica_sessao, cpf=CPF_B)
    _entrar(cliente_anonimo, cpf=CPF_A)
    assert cliente_anonimo.get("/me").json()["id"] == primeiro.id

    _entrar(cliente_anonimo, cpf=CPF_B)

    assert cliente_anonimo.get("/me").json()["id"] == segundo.id
