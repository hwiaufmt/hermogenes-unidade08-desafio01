from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

CAMPOS = {
    "nome": "nome",
    "categoria_id": "categoria",
    "quantidade": "quantidade",
    "estoque_minimo": "estoque mínimo",
    "cpf": "CPF",
    "email": "e-mail",
    "perfil": "perfil",
    "senha": "senha",
}
PREFIXO_PYDANTIC = "Value error, "
TIPOS_INTEIRO = {"int_type", "int_parsing", "int_from_float"}


def _nome_do_campo(erro: dict) -> str:
    campo = str(erro["loc"][-1])
    return CAMPOS.get(campo, campo)


def traduzir_erro(erro: dict) -> str:
    tipo = erro["type"]
    campo = _nome_do_campo(erro)
    if tipo == "json_invalid":
        return "O corpo da requisição não é um JSON válido."
    if tipo == "value_error":
        return str(erro["msg"]).removeprefix(PREFIXO_PYDANTIC)
    if campo == "categoria" and tipo in {"missing", *TIPOS_INTEIRO}:
        return "Selecione uma categoria."
    if tipo == "missing":
        return f"O campo '{campo}' é obrigatório."
    if tipo in TIPOS_INTEIRO:
        return f"O campo '{campo}' deve ser um número inteiro."
    if tipo == "greater_than_equal":
        return f"O campo '{campo}' deve ser maior ou igual a {erro['ctx']['ge']}."
    if tipo == "string_type":
        return f"O campo '{campo}' deve ser um texto."
    return f"Valor inválido no campo '{campo}'."


async def tratar_validacao(_: Request, erro: RequestValidationError) -> JSONResponse:
    mensagens = list(dict.fromkeys(traduzir_erro(e) for e in erro.errors()))
    return JSONResponse(status_code=422, content={"detail": " ".join(mensagens)})
