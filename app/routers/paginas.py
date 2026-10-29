from collections.abc import Callable
from pathlib import Path
from typing import Annotated, NamedTuple

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.config import SENHA_PADRAO
from app.dependencias import DbSessao, usuario_da_sessao
from app.models import Usuario
from app.permissoes import Acao, perfil_pode
from app.services.usuarios import PERFIS, TAMANHO_MINIMO_SENHA

router = APIRouter(include_in_schema=False)

templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


class ItemMenu(NamedTuple):
    chave: str
    rotulo: str
    url: str
    acoes: tuple[Acao, ...]


# O menu e o acesso às telas derivam da mesma matriz de permissões da API.
ITENS_MENU = (
    ItemMenu("pesquisa", "Pesquisa", "/pesquisa", (Acao.CONSULTAR_ESTOQUE,)),
    ItemMenu("movimentar", "Movimentar", "/movimentar", (Acao.MOVIMENTAR,)),
    ItemMenu(
        "cadastro",
        "Cadastro",
        "/materiais/novo",
        (Acao.CADASTRAR_MATERIAL, Acao.CRIAR_CATEGORIA, Acao.EDITAR_CATEGORIA),
    ),
    ItemMenu("usuarios", "Usuários", "/gestao/usuarios", (Acao.GERIR_USUARIOS,)),
)


class LoginNecessarioError(Exception):
    pass


class AcessoNegadoError(Exception):
    def __init__(self, usuario: Usuario) -> None:
        super().__init__("Acesso negado.")
        self.usuario = usuario


def menu_do_usuario(usuario: Usuario) -> list[ItemMenu]:
    return [i for i in ITENS_MENU if perfil_pode(usuario.perfil, *i.acoes)]


def acesso_pagina(*acoes: Acao) -> Callable[[Request, DbSessao], Usuario]:
    """Exige login (redireciona para /login) e ao menos uma das ações."""

    def verificar(request: Request, db: DbSessao) -> Usuario:
        usuario = usuario_da_sessao(request, db)
        if usuario is None:
            raise LoginNecessarioError()
        if not perfil_pode(usuario.perfil, *acoes):
            raise AcessoNegadoError(usuario)
        return usuario

    return verificar


def _pagina(
    request: Request,
    nome: str,
    usuario: Usuario | None,
    ativa: str | None,
    status_code: int = 200,
    **contexto: object,
) -> Response:
    menu = menu_do_usuario(usuario) if usuario else []
    contexto = {"usuario": usuario, "menu": menu, "ativa": ativa, **contexto}
    return templates.TemplateResponse(request, nome, contexto, status_code=status_code)


async def tratar_login_necessario(_: Request, __: LoginNecessarioError) -> Response:
    return RedirectResponse("/login", status_code=303)


async def tratar_acesso_negado(request: Request, erro: AcessoNegadoError) -> Response:
    return _pagina(request, "acesso_negado.html", erro.usuario, None, status_code=403)


PodePesquisar = Annotated[Usuario, Depends(acesso_pagina(Acao.CONSULTAR_ESTOQUE))]
PodeMovimentar = Annotated[Usuario, Depends(acesso_pagina(Acao.MOVIMENTAR))]
PodeCadastrar = Annotated[
    Usuario,
    Depends(
        acesso_pagina(
            Acao.CADASTRAR_MATERIAL, Acao.CRIAR_CATEGORIA, Acao.EDITAR_CATEGORIA
        )
    ),
]
PodeGerirUsuarios = Annotated[Usuario, Depends(acesso_pagina(Acao.GERIR_USUARIOS))]


@router.get("/")
def inicio(request: Request, db: DbSessao) -> Response:
    """Leva cada perfil à primeira tela a que tem acesso."""
    usuario = usuario_da_sessao(request, db)
    if usuario is None:
        return RedirectResponse("/login", status_code=303)
    menu = menu_do_usuario(usuario)
    if not menu:
        raise AcessoNegadoError(usuario)
    return RedirectResponse(menu[0].url, status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login(request: Request, db: DbSessao) -> Response:
    if usuario_da_sessao(request, db) is not None:
        return RedirectResponse("/", status_code=303)
    return _pagina(request, "login.html", None, "login")


@router.get("/pesquisa", response_class=HTMLResponse)
def pesquisa(request: Request, usuario: PodePesquisar) -> Response:
    return _pagina(request, "pesquisa.html", usuario, "pesquisa")


@router.get("/movimentar", response_class=HTMLResponse)
def movimentar(request: Request, usuario: PodeMovimentar) -> Response:
    return _pagina(request, "movimentar.html", usuario, "movimentar")


@router.get("/materiais/novo", response_class=HTMLResponse)
def cadastro(request: Request, usuario: PodeCadastrar) -> Response:
    return _pagina(
        request,
        "cadastro.html",
        usuario,
        "cadastro",
        pode_editar_categoria=perfil_pode(usuario.perfil, Acao.EDITAR_CATEGORIA),
    )


@router.get("/gestao/usuarios", response_class=HTMLResponse)
def usuarios(request: Request, usuario: PodeGerirUsuarios) -> Response:
    return _pagina(
        request,
        "usuarios.html",
        usuario,
        "usuarios",
        perfis=PERFIS,
        senha_padrao=SENHA_PADRAO,
        tamanho_minimo_senha=TAMANHO_MINIMO_SENHA,
    )
