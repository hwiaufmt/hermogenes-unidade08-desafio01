from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models import Categoria, Material, Movimentacao

CATEGORIAS_INICIAIS = ("Papelaria", "Escrita", "Informática")
STATUS_DISPONIVEL = "Disponível"
STATUS_INDISPONIVEL = "Indisponível"
TIPO_ENTRADA = "entrada"
TIPO_SAIDA = "saida"


class MaterialInexistenteError(Exception):
    def __init__(self, material_id: int) -> None:
        super().__init__(f"O material {material_id} não existe.")


class QuantidadeInvalidaError(Exception):
    def __init__(self) -> None:
        super().__init__("A quantidade deve ser um número inteiro maior que zero.")


class SaldoInsuficienteError(Exception):
    def __init__(self, nome: str, saldo: int, solicitada: int) -> None:
        super().__init__(
            f"Saldo insuficiente de '{nome}': disponível {saldo}, "
            f"solicitado {solicitada}."
        )


class CategoriaInexistenteError(Exception):
    def __init__(self, categoria_id: int) -> None:
        super().__init__(f"A categoria {categoria_id} não existe.")


class CategoriaDuplicadaError(Exception):
    def __init__(self, nome: str) -> None:
        super().__init__(f"Já existe uma categoria chamada '{nome}'.")


def listar_categorias(db: Session) -> list[Categoria]:
    return list(db.scalars(select(Categoria).order_by(Categoria.nome)))


def criar_categoria(db: Session, nome: str) -> Categoria:
    categoria = Categoria(nome=nome)
    db.add(categoria)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise CategoriaDuplicadaError(nome) from None
    return categoria


def calcular_status(quantidade: int) -> str:
    return STATUS_INDISPONIVEL if quantidade == 0 else STATUS_DISPONIVEL


def listar_materiais(db: Session, categoria_id: int | None = None) -> list[Material]:
    consulta = (
        select(Material).options(joinedload(Material.categoria)).order_by(Material.nome)
    )
    if categoria_id is not None:
        if db.get(Categoria, categoria_id) is None:
            raise CategoriaInexistenteError(categoria_id)
        consulta = consulta.where(Material.categoria_id == categoria_id)
    return list(db.scalars(consulta))


def criar_material(
    db: Session,
    nome: str,
    categoria_id: int,
    quantidade: int = 0,
    estoque_minimo: int = 0,
) -> Material:
    categoria = db.get(Categoria, categoria_id)
    if categoria is None:
        raise CategoriaInexistenteError(categoria_id)
    material = Material(
        nome=nome,
        categoria=categoria,
        quantidade=quantidade,
        estoque_minimo=estoque_minimo,
    )
    db.add(material)
    db.commit()
    return material


def obter_material(db: Session, material_id: int) -> Material:
    consulta = (
        select(Material)
        .options(joinedload(Material.categoria))
        .where(Material.id == material_id)
        .execution_options(populate_existing=True)
    )
    material = db.scalar(consulta)
    if material is None:
        raise MaterialInexistenteError(material_id)
    return material


def _validar_quantidade(quantidade: int) -> None:
    if quantidade <= 0:
        raise QuantidadeInvalidaError()


def _gravar_movimentacao(
    db: Session, material_id: int, tipo: str, quantidade: int, saldo_apos: int
) -> None:
    db.add(
        Movimentacao(
            material_id=material_id,
            tipo=tipo,
            quantidade=quantidade,
            saldo_apos=saldo_apos,
        )
    )


def registrar_entrada(db: Session, material_id: int, quantidade: int) -> Material:
    _validar_quantidade(quantidade)
    saldo_apos = db.scalar(
        update(Material)
        .where(Material.id == material_id)
        .values(quantidade=Material.quantidade + quantidade)
        .returning(Material.quantidade)
    )
    if saldo_apos is None:
        db.rollback()
        raise MaterialInexistenteError(material_id)
    _gravar_movimentacao(db, material_id, TIPO_ENTRADA, quantidade, saldo_apos)
    db.commit()
    return obter_material(db, material_id)


def registrar_saida(db: Session, material_id: int, quantidade: int) -> Material:
    _validar_quantidade(quantidade)
    saldo_apos = db.scalar(
        update(Material)
        .where(Material.id == material_id, Material.quantidade >= quantidade)
        .values(quantidade=Material.quantidade - quantidade)
        .returning(Material.quantidade)
    )
    if saldo_apos is None:
        db.rollback()
        material = obter_material(db, material_id)
        raise SaldoInsuficienteError(material.nome, material.quantidade, quantidade)
    _gravar_movimentacao(db, material_id, TIPO_SAIDA, quantidade, saldo_apos)
    db.commit()
    return obter_material(db, material_id)


def semear_categorias(db: Session) -> None:
    existentes = {c.nome for c in listar_categorias(db)}
    for nome in CATEGORIAS_INICIAIS:
        if nome not in existentes:
            db.add(Categoria(nome=nome))
    db.commit()
