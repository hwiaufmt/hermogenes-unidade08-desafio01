import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.config import SENHA_PADRAO
from app.models import Usuario
from app.seguranca import gerar_hash, verificar_senha
from app.services.usuarios import (
    PERFIL_ADMINISTRADOR,
    cpf_valido,
    formatar_cpf,
    normalizar_cpf,
)
from tests.conftest import CPFS_DE_TESTE

CPF_A = "52998224725"
CPF_B = "11144477735"
CPF_ADMIN_DO_TESTE = CPFS_DE_TESTE[PERFIL_ADMINISTRADOR]


def _dados(**alteracoes: object) -> dict:
    dados = {
        "nome": "Maria Silva",
        "cpf": CPF_A,
        "email": "maria@exemplo.com",
        "perfil": "estoquista",
        "senha": "senha-segura-1",
    }
    return {**dados, **alteracoes}


def _criar(client: TestClient, **alteracoes: object) -> dict:
    resposta = client.post("/usuarios", json=_dados(**alteracoes))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_cpf_valido_aceita_cpfs_reais_e_rejeita_invalidos() -> None:
    assert cpf_valido(CPF_A)
    assert cpf_valido(CPF_B)
    assert cpf_valido("12345678909")
    assert not cpf_valido("52998224724")  # dígito verificador errado
    assert not cpf_valido("11111111111")  # todos iguais
    assert not cpf_valido("123")  # tamanho
    assert not cpf_valido("5299822472a")  # não numérico


def test_normalizar_e_formatar_cpf() -> None:
    assert normalizar_cpf("529.982.247-25") == CPF_A
    assert formatar_cpf(CPF_A) == "529.982.247-25"


def test_hash_de_senha_nao_guarda_texto_puro_e_verifica() -> None:
    hash_guardado = gerar_hash("minha-senha-1")

    assert "minha-senha-1" not in hash_guardado
    assert verificar_senha("minha-senha-1", hash_guardado)
    assert not verificar_senha("outra-senha", hash_guardado)
    assert gerar_hash("minha-senha-1") != hash_guardado  # sal aleatório
    assert not verificar_senha("x", "lixo")


def test_cadastra_usuario_com_nome_cpf_e_email(client: TestClient) -> None:
    resposta = client.post(
        "/usuarios", json=_dados(cpf="529.982.247-25", email=" Maria@Exemplo.COM ")
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["nome"] == "Maria Silva"
    assert corpo["cpf"] == CPF_A
    assert corpo["email"] == "maria@exemplo.com"
    assert corpo["perfil"] == "estoquista"
    assert corpo["ativo"] is True
    assert "senha" not in corpo
    assert "senha_hash" not in corpo


def test_senha_e_gravada_somente_com_hash(
    client: TestClient, fabrica_sessao: sessionmaker[Session]
) -> None:
    _criar(client)

    with fabrica_sessao() as db:
        usuario = db.scalar(select(Usuario).where(Usuario.cpf == CPF_A))
        assert usuario.senha_hash != "senha-segura-1"
        assert verificar_senha("senha-segura-1", usuario.senha_hash)


def test_ca07_cpf_duplicado_nao_e_permitido(client: TestClient) -> None:
    _criar(client)

    resposta = client.post(
        "/usuarios", json=_dados(nome="Outra Pessoa", email="outra@exemplo.com")
    )

    assert resposta.status_code == 409
    assert resposta.json()["detail"] == "Já existe um usuário com o CPF 529.982.247-25."
    assert len(client.get("/usuarios").json()) == 2  # administrador do teste + Maria


def test_ca07_cpf_duplicado_com_mascara_diferente_tambem_e_bloqueado(
    client: TestClient,
) -> None:
    _criar(client, cpf="529.982.247-25")

    resposta = client.post("/usuarios", json=_dados(cpf="52998224725"))

    assert resposta.status_code == 409
    assert len(client.get("/usuarios").json()) == 2


def test_ca07_cpf_duplicado_vale_tambem_para_usuario_inativo(
    client: TestClient,
) -> None:
    admin = _criar(client, cpf=CPF_B, perfil="administrador")
    usuario = _criar(client)
    client.post(f"/usuarios/{usuario['id']}/inativar")

    resposta = client.post("/usuarios", json=_dados())

    assert resposta.status_code == 409
    assert admin["id"] != usuario["id"]


def test_ca07_email_repetido_com_cpf_diferente_e_permitido(
    client: TestClient,
) -> None:
    _criar(client)

    resposta = client.post("/usuarios", json=_dados(cpf=CPF_B))

    assert resposta.status_code == 201


@pytest.mark.parametrize(
    ("alteracoes", "esperado"),
    [
        ({"cpf": "52998224724"}, "CPF inválido."),
        ({"cpf": "111.111.111-11"}, "CPF inválido."),
        ({"cpf": ""}, "CPF inválido."),
        ({"nome": "  "}, "O nome do usuário é obrigatório."),
        ({"email": "sem-arroba"}, "O e-mail informado é inválido."),
        (
            {"perfil": "chefe"},
            "Perfil inválido. Use administrador, estoquista ou operador.",
        ),
        ({"senha": "12345"}, "A senha deve ter pelo menos 6 caracteres."),
    ],
)
def test_cadastro_de_usuario_rejeita_dados_invalidos(
    client: TestClient, alteracoes: dict, esperado: str
) -> None:
    resposta = client.post("/usuarios", json=_dados(**alteracoes))

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == esperado
    cpfs = [u["cpf"] for u in client.get("/usuarios").json()]
    assert cpfs == [CPF_ADMIN_DO_TESTE]  # nenhum usuário novo foi gravado


def test_cadastro_de_usuario_com_campo_ausente_devolve_mensagem_em_portugues(
    client: TestClient,
) -> None:
    resposta = client.post("/usuarios", json={"nome": "Maria"})

    assert resposta.status_code == 422
    detalhe = resposta.json()["detail"]
    assert "O campo 'CPF' é obrigatório." in detalhe
    assert "O campo 'e-mail' é obrigatório." in detalhe


def test_lista_e_consulta_de_usuarios(client: TestClient) -> None:
    _criar(client, nome="Zeca", cpf=CPF_B, email="zeca@exemplo.com")
    maria = _criar(client)

    nomes = [u["nome"] for u in client.get("/usuarios").json()]
    consulta = client.get(f"/usuarios/{maria['id']}")

    assert nomes == ["Administrador", "Maria Silva", "Zeca"]
    assert consulta.status_code == 200
    assert consulta.json()["cpf"] == CPF_A
    assert client.get("/usuarios/999").status_code == 404


def test_atualiza_nome_email_e_perfil_mantendo_o_cpf(client: TestClient) -> None:
    usuario = _criar(client)

    resposta = client.put(
        f"/usuarios/{usuario['id']}",
        json={
            "nome": "Maria Souza",
            "email": "maria.souza@exemplo.com",
            "perfil": "operador",
        },
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["nome"] == "Maria Souza"
    assert corpo["email"] == "maria.souza@exemplo.com"
    assert corpo["perfil"] == "operador"
    assert corpo["cpf"] == CPF_A


def test_atualiza_senha_somente_quando_informada(
    client: TestClient, fabrica_sessao: sessionmaker[Session]
) -> None:
    usuario = _criar(client)
    base = {"nome": "Maria", "email": "maria@exemplo.com", "perfil": "estoquista"}

    def hash_atual() -> str:
        with fabrica_sessao() as db:
            return db.scalar(select(Usuario).where(Usuario.cpf == CPF_A)).senha_hash

    client.put(f"/usuarios/{usuario['id']}", json=base)
    assert verificar_senha("senha-segura-1", hash_atual())

    client.put(f"/usuarios/{usuario['id']}", json={**base, "senha": "nova-senha-9"})
    assert verificar_senha("nova-senha-9", hash_atual())


def test_atualizar_usuario_inexistente_retorna_404(client: TestClient) -> None:
    resposta = client.put(
        "/usuarios/999",
        json={"nome": "X", "email": "x@exemplo.com", "perfil": "operador"},
    )

    assert resposta.status_code == 404


def test_inativa_e_reativa_usuario_sem_apagar(client: TestClient) -> None:
    usuario = _criar(client)

    inativo = client.post(f"/usuarios/{usuario['id']}/inativar")
    assert inativo.status_code == 200
    assert inativo.json()["ativo"] is False
    assert len(client.get("/usuarios").json()) == 2  # continua listado, só inativo

    ativo = client.post(f"/usuarios/{usuario['id']}/reativar")
    assert ativo.json()["ativo"] is True
    assert client.post("/usuarios/999/inativar").status_code == 404
    assert client.post("/usuarios/999/reativar").status_code == 404


def test_nao_inativa_nem_rebaixa_o_ultimo_administrador(client: TestClient) -> None:
    admin = client.get("/me").json()  # único administrador: o do próprio teste

    inativar = client.post(f"/usuarios/{admin['id']}/inativar")
    rebaixar = client.put(
        f"/usuarios/{admin['id']}",
        json={"nome": "Maria", "email": "maria@exemplo.com", "perfil": "operador"},
    )

    assert inativar.status_code == 409
    assert rebaixar.status_code == 409
    assert "último administrador" in inativar.json()["detail"]
    assert client.get(f"/usuarios/{admin['id']}").json()["ativo"] is True


def test_com_dois_administradores_um_pode_ser_inativado(client: TestClient) -> None:
    primeiro = _criar(client, perfil="administrador")
    _criar(client, cpf=CPF_B, email="b@exemplo.com", perfil="administrador")

    resposta = client.post(f"/usuarios/{primeiro['id']}/inativar")

    assert resposta.status_code == 200


def test_usuario_sem_senha_informada_recebe_a_senha_padrao(
    client: TestClient, cliente_anonimo: TestClient
) -> None:
    corpo = {k: v for k, v in _dados().items() if k != "senha"}

    criado = client.post("/usuarios", json=corpo)
    cliente_anonimo.post("/logout")
    entrada = cliente_anonimo.post("/login", json={"cpf": CPF_A, "senha": SENHA_PADRAO})

    assert criado.status_code == 201
    assert SENHA_PADRAO == "123456"
    assert entrada.status_code == 200
    assert entrada.json()["cpf"] == CPF_A


def test_senha_com_seis_caracteres_e_aceita_e_com_cinco_nao(
    client: TestClient,
) -> None:
    aceita = client.post("/usuarios", json=_dados(senha="123456"))
    recusada = client.post("/usuarios", json=_dados(cpf=CPF_B, senha="12345"))

    assert aceita.status_code == 201
    assert recusada.status_code == 422
