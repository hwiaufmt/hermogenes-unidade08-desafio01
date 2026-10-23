from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    computed_field,
    field_validator,
)

from app.services.estoque import calcular_status


class CategoriaCriar(BaseModel):
    nome: str

    @field_validator("nome")
    @classmethod
    def nome_nao_vazio(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("O nome da categoria é obrigatório.")
        return valor


class CategoriaSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str


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
