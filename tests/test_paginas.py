from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app import permissoes
from app.permissoes import Acao
from app.services.usuarios import (
    PERFIL_ADMINISTRADOR,
    PERFIL_ESTOQUISTA,
    PERFIL_OPERADOR,
    PERFIS,
)

ADMIN = PERFIL_ADMINISTRADOR
ESTOQUISTA = PERFIL_ESTOQUISTA
OPERADOR = PERFIL_OPERADOR

# página -> perfis autorizados (matriz real)
PAGINAS = {
    "/pesquisa": {ESTOQUISTA, OPERADOR},
    "/movimentar": {OPERADOR},
    "/materiais/novo": {ESTOQUISTA},
    "/gestao/usuarios": {ADMIN},
}
MENU_POR_PERFIL = {
    ESTOQUISTA: ["/pesquisa", "/materiais/novo"],
    OPERADOR: ["/pesquisa", "/movimentar"],
    ADMIN: ["/gestao/usuarios"],
}


def _links_do_menu(html: str) -> list[str]:
    inicio = html.index('<nav aria-label="Principal">')
    trecho = html[inicio : html.index("</nav>", inicio)]
    return [parte.split('"')[0] for parte in trecho.split('href="')[1:]]


def test_pagina_login_renderiza_sem_menu(cliente_anonimo: TestClient) -> None:
    resposta = cliente_anonimo.get("/login")

    assert resposta.status_code == 200
    assert 'for="login-cpf"' in resposta.text
    assert 'for="login-senha"' in resposta.text
    assert "js/login.js" in resposta.text
    assert "Principal" not in resposta.text
    assert "botao-sair" not in resposta.text


def test_raiz_sem_login_redireciona_para_o_login(cliente_anonimo: TestClient) -> None:
    resposta = cliente_anonimo.get("/", follow_redirects=False)

    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/login"


@pytest.mark.parametrize("caminho", sorted(PAGINAS))
def test_ca08_pagina_sem_login_redireciona_para_o_login(
    cliente_anonimo: TestClient, caminho: str
) -> None:
    resposta = cliente_anonimo.get(caminho, follow_redirects=False)

    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/login"


@pytest.mark.parametrize("perfil", sorted(PERFIS))
@pytest.mark.parametrize("caminho", sorted(PAGINAS))
def test_ca08_cada_perfil_abre_somente_as_paginas_que_lhe_cabem(
    entrar_como: Callable[[str], TestClient], perfil: str, caminho: str
) -> None:
    client = entrar_como(perfil)

    resposta = client.get(caminho, follow_redirects=False)

    if perfil in PAGINAS[caminho]:
        assert resposta.status_code == 200
    else:
        assert resposta.status_code == 403
        assert "Acesso negado" in resposta.text
        assert perfil in resposta.text


@pytest.mark.parametrize(
    ("perfil", "destino"),
    [
        (ESTOQUISTA, "/pesquisa"),
        (OPERADOR, "/pesquisa"),
        (ADMIN, "/gestao/usuarios"),
    ],
)
def test_raiz_leva_cada_perfil_a_sua_primeira_tela(
    entrar_como: Callable[[str], TestClient], perfil: str, destino: str
) -> None:
    client = entrar_como(perfil)

    resposta = client.get("/", follow_redirects=False)

    assert resposta.status_code == 303
    assert resposta.headers["location"] == destino


@pytest.mark.parametrize("perfil", sorted(PERFIS))
def test_ca08_menu_mostra_somente_o_que_o_perfil_acessa(
    entrar_como: Callable[[str], TestClient], perfil: str
) -> None:
    client = entrar_como(perfil)
    inicial = MENU_POR_PERFIL[perfil][0]

    html = client.get(inicial).text

    assert _links_do_menu(html) == MENU_POR_PERFIL[perfil]
    assert 'id="botao-sair"' in html
    assert perfil in html


def test_pagina_de_acesso_negado_oferece_caminho_de_volta(
    entrar_como: Callable[[str], TestClient],
) -> None:
    client = entrar_como(OPERADOR)

    resposta = client.get("/gestao/usuarios")

    assert resposta.status_code == 403
    assert 'href="/pesquisa"' in resposta.text


def test_login_ja_autenticado_redireciona_para_a_raiz(
    entrar_como: Callable[[str], TestClient],
) -> None:
    client = entrar_como(OPERADOR)

    resposta = client.get("/login", follow_redirects=False)

    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/"


def test_sair_encerra_a_sessao_e_bloqueia_as_paginas(
    entrar_como: Callable[[str], TestClient],
) -> None:
    client = entrar_como(OPERADOR)
    assert client.get("/pesquisa").status_code == 200

    client.post("/logout")

    resposta = client.get("/pesquisa", follow_redirects=False)
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/login"


def test_pagina_pesquisa_renderiza_com_filtros(client: TestClient) -> None:
    html = client.get("/pesquisa").text

    assert 'for="filtro-busca"' in html
    assert 'for="filtro-categoria"' in html
    assert 'for="filtro-status"' in html
    assert 'id="grupos"' in html
    assert "js/pesquisa.js" in html


def test_pagina_movimentar_renderiza(client: TestClient) -> None:
    html = client.get("/movimentar").text

    assert 'for="movimento-material"' in html
    assert 'for="movimento-quantidade"' in html
    assert "js/movimentar.js" in html


def test_pagina_cadastro_renderiza_e_nao_conflita_com_material_por_id(
    client: TestClient,
) -> None:
    resposta = client.get("/materiais/novo")

    assert resposta.status_code == 200
    assert 'for="material-nome"' in resposta.text
    assert "Nova categoria" in resposta.text


def test_pagina_cadastro_tem_lista_de_categorias_e_dialogos_de_edicao(
    client: TestClient,
) -> None:
    html = client.get("/materiais/novo").text

    assert 'id="lista-categorias"' in html
    assert 'id="dialogo-edicao"' in html
    assert 'for="edicao-nome"' in html
    assert 'id="dialogo-confirmacao"' in html
    assert 'id="texto-confirmacao"' in html
    assert 'data-pode-editar="sim"' in html
    assert '<th scope="col">Ações</th>' in html


def test_ca09_estoquista_ve_a_edicao_de_categorias_na_tela(
    entrar_como: Callable[[str], TestClient],
) -> None:
    html = entrar_como(ESTOQUISTA).get("/materiais/novo").text

    assert 'data-pode-editar="sim"' in html


def test_ca09_sem_a_permissao_de_editar_a_tela_nao_oferece_a_edicao(
    entrar_como: Callable[[str], TestClient], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        permissoes,
        "PERMISSOES",
        {ESTOQUISTA: frozenset({Acao.CRIAR_CATEGORIA, Acao.CADASTRAR_MATERIAL})},
    )

    html = entrar_como(ESTOQUISTA).get("/materiais/novo").text

    assert 'data-pode-editar="nao"' in html
    assert '<th scope="col">Ações</th>' not in html


def test_ca09_quem_so_pode_editar_categoria_abre_a_pagina_de_cadastro(
    entrar_como: Callable[[str], TestClient], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        permissoes, "PERMISSOES", {ESTOQUISTA: frozenset({Acao.EDITAR_CATEGORIA})}
    )
    client = entrar_como(ESTOQUISTA)

    resposta = client.get("/materiais/novo")

    assert resposta.status_code == 200
    assert "/materiais/novo" in resposta.text  # item "Cadastro" no menu


def test_pagina_usuarios_renderiza_com_os_perfis(client: TestClient) -> None:
    html = client.get("/gestao/usuarios").text

    for rotulo in ("usuario-nome", "usuario-cpf", "usuario-email", "usuario-senha"):
        assert f'for="{rotulo}"' in html
    for perfil in PERFIS:
        assert f'value="{perfil}"' in html
    assert "js/usuarios.js" in html


def test_arquivos_estaticos_sao_servidos(client: TestClient) -> None:
    for caminho in (
        "css/styles.css",
        "js/api.js",
        "js/login.js",
        "js/sair.js",
        "js/pesquisa.js",
        "js/cadastro.js",
        "js/movimentar.js",
        "js/usuarios.js",
    ):
        assert client.get(f"/static/{caminho}").status_code == 200
