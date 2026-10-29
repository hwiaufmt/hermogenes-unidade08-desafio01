from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    computed_field,
    field_validator,
)

from app.config import SENHA_PADRAO
from app.services.estoque import calcular_status
from app.services.usuarios import (
    PERFIS,
    TAMANHO_MINIMO_SENHA,
    cpf_valido,
    email_valido,
    normalizar_cpf,
)


class CategoriaCriar(BaseModel):
    nome: str

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("O nome da categoria é obrigatório.")
        return valor


class CategoriaAtualizar(CategoriaCriar):
    confirmar: bool = False


class CategoriaSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str


class CategoriaComTotal(CategoriaSaida):
    total_materiais: int


class MaterialCriar(BaseModel):
    nome: str
    categoria_id: int
    quantidade: int = Field(default=0, ge=0)
    estoque_minimo: int = Field(default=0, ge=0)

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("O nome do material é obrigatório.")
        return valor


def _validar_nome_usuario(valor: str) -> str:
    valor = valor.strip()
    if not valor:
        raise ValueError("O nome do usuário é obrigatório.")
    return valor


def _validar_email(valor: str) -> str:
    valor = valor.strip().lower()
    if not email_valido(valor):
        raise ValueError("O e-mail informado é inválido.")
    return valor


def _validar_perfil(valor: str) -> str:
    valor = valor.strip().lower()
    if valor not in PERFIS:
        raise ValueError("Perfil inválido. Use administrador, estoquista ou operador.")
    return valor


def _validar_senha(valor: str) -> str:
    if len(valor) < TAMANHO_MINIMO_SENHA:
        raise ValueError(
            f"A senha deve ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres."
        )
    return valor


class UsuarioCriar(BaseModel):
    nome: str
    cpf: str
    email: str
    perfil: str
    senha: str = SENHA_PADRAO  # protótipo: sem senha informada, vale a padrão

    _nome = field_validator("nome")(_validar_nome_usuario)
    _email = field_validator("email")(_validar_email)
    _perfil = field_validator("perfil")(_validar_perfil)
    _senha = field_validator("senha")(_validar_senha)

    @field_validator("cpf")
    @classmethod
    def cpf_com_digitos_validos(cls, valor: str) -> str:
        cpf = normalizar_cpf(valor)
        if not cpf_valido(cpf):
            raise ValueError("CPF inválido.")
        return cpf


class UsuarioAtualizar(BaseModel):
    nome: str
    email: str
    perfil: str
    senha: str | None = None

    _nome = field_validator("nome")(_validar_nome_usuario)
    _email = field_validator("email")(_validar_email)
    _perfil = field_validator("perfil")(_validar_perfil)

    @field_validator("senha")
    @classmethod
    def senha_opcional(cls, valor: str | None) -> str | None:
        return None if valor is None else _validar_senha(valor)


class LoginEntrada(BaseModel):
    cpf: str
    senha: str


class UsuarioSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    cpf: str
    email: str
    perfil: str
    ativo: bool


class MovimentacaoCriar(BaseModel):
    quantidade: StrictInt

    @field_validator("quantidade")
    @classmethod
    def quantidade_positiva(cls, valor: int) -> int:
        if valor <= 0:
            raise ValueError("A quantidade deve ser um número inteiro maior que zero.")
        return valor


class MaterialSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    categoria: CategoriaSaida
    quantidade: int
    estoque_minimo: int

    @computed_field
    @property
    def status(self) -> str:
        return calcular_status(self.quantidade)
