from fastapi.testclient import TestClient


def test_pagina_estoque_renderiza(client: TestClient) -> None:
    resposta = client.get("/")

    assert resposta.status_code == 200
    assert "Estoque" in resposta.text
    assert "js/estoque.js" in resposta.text


def test_pagina_cadastro_renderiza(client: TestClient) -> None:
    resposta = client.get("/materiais/novo")

    assert resposta.status_code == 200
    assert 'for="material-nome"' in resposta.text
    assert "Nova categoria" in resposta.text


def test_pagina_movimentar_renderiza(client: TestClient) -> None:
    resposta = client.get("/movimentar")

    assert resposta.status_code == 200
    assert 'for="movimento-material"' in resposta.text
    assert 'for="movimento-quantidade"' in resposta.text
    assert "js/movimentar.js" in resposta.text


def test_arquivos_estaticos_sao_servidos(client: TestClient) -> None:
    for caminho in (
        "css/styles.css",
        "js/api.js",
        "js/cadastro.js",
        "js/estoque.js",
        "js/movimentar.js",
    ):
        assert client.get(f"/static/{caminho}").status_code == 200
