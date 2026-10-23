from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(include_in_schema=False)

templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/", response_class=HTMLResponse)
def estoque(request: Request):
    return templates.TemplateResponse(request, "estoque.html", {"ativa": "estoque"})


@router.get("/movimentar", response_class=HTMLResponse)
def movimentar(request: Request):
    return templates.TemplateResponse(
        request, "movimentar.html", {"ativa": "movimentar"}
    )


@router.get("/materiais/novo", response_class=HTMLResponse)
def cadastro(request: Request):
    return templates.TemplateResponse(request, "cadastro.html", {"ativa": "cadastro"})
