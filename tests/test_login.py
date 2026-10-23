from fastapi.testclient import TestClient

CPF_A = "52998224725"
CPF_B = "11144477735"
SENHA = "senha-segura-1"


def _criar_usuario(
    client: TestClient, cpf: str = CPF_A, perfil: str = "operador"
) -> dict:
    resposta = client.post(
        "/usuarios",
        json={
            "nome": "Maria Silva",
            "cpf": cpf,
            "email": "maria@exemplo.com",
            "perfil": perfil,
            "senha": SENHA,
        },
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _entrar(client: TestClient, cpf: str = CPF_A, senha: str = SENHA):
    return client.post("/login", json={"cpf": cpf, "senha": senha})


def test_login_com_cpf_e_senha_corretos_abre_sessao(client: TestClient) -> None:
    usuario = _criar_usuario(client)

    resposta = _entrar(client)

    assert resposta.status_code == 200
    assert resposta.json()["id"] == usuario["id"]
    assert "senha" not in resposta.json()
    assert client.get("/me").json()["cpf"] == CPF_A


def test_login_aceita_cpf_com_mascara(client: TestClient) -> None:
    _criar_usuario(client)

    assert _entrar(client, cpf="529.982.247-25").status_code == 200


def test_login_com_senha_errada_e_rejeitado(client: TestClient) -> None:
    _criar_usuario(client)

    resposta = _entrar(client, senha="senha-errada-1")

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "CPF ou senha inválidos."
    assert client.get("/me").status_code == 401


def test_login_nao_revela_se_o_cpf_existe(client: TestClient) -> None:
    _criar_usuario(client)

    senha_errada = _entrar(client, senha="senha-errada-1")
    cpf_inexistente = _entrar(client, cpf=CPF_B)

    assert senha_errada.status_code == cpf_inexistente.status_code == 401
    assert senha_errada.json() == cpf_inexistente.json()


def test_usuario_inativo_nao_consegue_entrar(client: TestClient) -> None:
    usuario = _criar_usuario(client)
    client.post(f"/usuarios/{usuario['id']}/inativar")

    resposta = _entrar(client)

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "CPF ou senha inválidos."


def test_me_sem_login_retorna_401(client: TestClient) -> None:
    resposta = client.get("/me")

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "É necessário entrar no sistema."


def test_logout_encerra_a_sessao(client: TestClient) -> None:
    _criar_usuario(client)
    _entrar(client)

    resposta = client.post("/logout")

    assert resposta.status_code == 204
    assert client.get("/me").status_code == 401


def test_inativar_usuario_derruba_a_sessao_em_andamento(client: TestClient) -> None:
    _criar_usuario(client, cpf=CPF_B, perfil="administrador")
    usuario = _criar_usuario(client, perfil="administrador")
    _entrar(client)
    assert client.get("/me").status_code == 200

    client.post(f"/usuarios/{usuario['id']}/inativar")

    assert client.get("/me").status_code == 401


def test_cookie_de_sessao_adulterado_e_ignorado(client: TestClient) -> None:
    _criar_usuario(client)
    _entrar(client)
    client.cookies.set("session", "valor-forjado")

    assert client.get("/me").status_code == 401


def test_cookie_de_sessao_e_httponly_e_samesite(client: TestClient) -> None:
    _criar_usuario(client)

    cookie = _entrar(client).headers["set-cookie"].lower()

    assert "httponly" in cookie
    assert "samesite=lax" in cookie


def test_login_sem_senha_devolve_mensagem_em_portugues(client: TestClient) -> None:
    resposta = client.post("/login", json={"cpf": CPF_A})

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "O campo 'senha' é obrigatório."


def test_login_troca_a_sessao_anterior(client: TestClient) -> None:
    primeiro = _criar_usuario(client, cpf=CPF_A)
    segundo = _criar_usuario(client, cpf=CPF_B)
    _entrar(client, cpf=CPF_A)
    assert client.get("/me").json()["id"] == primeiro["id"]

    _entrar(client, cpf=CPF_B)

    assert client.get("/me").json()["id"] == segundo["id"]
