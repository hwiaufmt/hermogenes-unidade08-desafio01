from datetime import UTC, datetime
from typing import NamedTuple

from sqlalchemy import func, select, update
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


class ConfirmacaoNecessariaError(Exception):
    """A alteração afeta registros existentes e ainda não foi confirmada."""

    def __init__(self, afetados: int) -> None:
        self.afetados = afetados
        materiais = _plural(afetados, "material", "materiais")
        registros = _plural(afetados, "registro", "registros")
        super().__init__(
            f"Esta categoria tem {afetados} {materiais}; "
            f"a mudança de nome afetará {afetados} {registros}. "
            "Confirme para gravar."
        )


class ConfirmacaoDeExclusaoError(Exception):
    """O material tem saldo e a exclusão ainda não foi confirmada."""

    def __init__(self, nome: str, saldo: int) -> None:
        self.saldo = saldo
        unidades = _plural(saldo, "unidade", "unidades")
        super().__init__(
            f"O material '{nome}' tem {saldo} {unidades} em estoque; "
            "ao excluir, ele deixa de aparecer no sistema. Confirme para excluir."
        )


class ResumoCategoria(NamedTuple):
    id: int
    nome: str
    total_materiais: int


def _plural(quantidade: int, singular: str, plural: str) -> str:
    return singular if quantidade == 1 else plural


def listar_categorias(db: Session) -> list[Categoria]:
    return list(db.scalars(select(Categoria).order_by(Categoria.nome)))


def listar_categorias_com_totais(db: Session) -> list[ResumoCategoria]:
    consulta = (
        select(Categoria.id, Categoria.nome, func.count(Material.id))
        .outerjoin(
            Material,
            (Material.categoria_id == Categoria.id) & Material.excluido_em.is_(None),
        )
        .group_by(Categoria.id, Categoria.nome)
        .order_by(Categoria.nome)
    )
    return [ResumoCategoria(*linha) for linha in db.execute(consulta)]


class SaldoDaCategoria(NamedTuple):
    categoria: Categoria
    materiais: list[Material]
    total_materiais: int
    total_unidades: int
    total_indisponiveis: int


class TotaisDeSaldo(NamedTuple):
    total_materiais: int
    total_unidades: int
    total_indisponiveis: int


class ConsultaDeSaldos(NamedTuple):
    categorias: list[SaldoDaCategoria]
    totais: TotaisDeSaldo


def _saldo_da_categoria(
    categoria: Categoria, materiais: list[Material]
) -> SaldoDaCategoria:
    indisponiveis = sum(
        1 for m in materiais if calcular_status(m.quantidade) == STATUS_INDISPONIVEL
    )
    unidades = sum(m.quantidade for m in materiais)
    return SaldoDaCategoria(
        categoria, materiais, len(materiais), unidades, indisponiveis
    )


def consultar_saldos(db: Session) -> ConsultaDeSaldos:
    """Saldos agrupados por categoria, com totais por categoria e geral.

    Inclui as categorias sem materiais (com zeros). Categorias e materiais saem
    em ordem alfabética, sem diferenciar maiúsculas de minúsculas.
    """
    categorias = sorted(listar_categorias(db), key=lambda c: c.nome.casefold())
    por_categoria: dict[int, list[Material]] = {c.id: [] for c in categorias}
    for material in db.scalars(select(Material).where(Material.excluido_em.is_(None))):
        if material.categoria_id in por_categoria:
            por_categoria[material.categoria_id].append(material)
    saldos = [
        _saldo_da_categoria(
            categoria,
            sorted(por_categoria[categoria.id], key=lambda m: m.nome.casefold()),
        )
        for categoria in categorias
    ]
    totais = TotaisDeSaldo(
        total_materiais=sum(s.total_materiais for s in saldos),
        total_unidades=sum(s.total_unidades for s in saldos),
        total_indisponiveis=sum(s.total_indisponiveis for s in saldos),
    )
    return ConsultaDeSaldos(saldos, totais)


def _contar_materiais_da_categoria(db: Session, categoria_id: int) -> int:
    consulta = select(func.count(Material.id)).where(
        Material.categoria_id == categoria_id, Material.excluido_em.is_(None)
    )
    return db.scalar(consulta) or 0


def atualizar_categoria(
    db: Session, categoria_id: int, nome: str, confirmar: bool = False
) -> ResumoCategoria:
    """Altera o nome da categoria.

    Se a categoria tem materiais, a alteração só é gravada com `confirmar`; sem
    ela, informa quantos registros seriam afetados (CA-10). Nome repetido é
    recusado antes de pedir a confirmação.
    """
    categoria = db.get(Categoria, categoria_id)
    if categoria is None:
        raise CategoriaInexistenteError(categoria_id)
    total = _contar_materiais_da_categoria(db, categoria_id)
    if nome == categoria.nome:
        return ResumoCategoria(categoria.id, categoria.nome, total)
    repetida = _categoria_com_nome(db, nome, ignorar_id=categoria_id)
    if repetida is not None:
        raise CategoriaDuplicadaError(repetida.nome)
    if total > 0 and not confirmar:
        raise ConfirmacaoNecessariaError(total)
    categoria.nome = nome
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise CategoriaDuplicadaError(nome) from None
    return ResumoCategoria(categoria.id, categoria.nome, total)


def _categoria_com_nome(
    db: Session, nome: str, ignorar_id: int | None = None
) -> Categoria | None:
    """Categoria com este nome, **sem diferenciar maiúsculas de minúsculas**
    ("Escrita" é igual a "escrita"). A comparação é feita aqui, com `casefold`,
    porque o `lower()` do SQLite só trata letras ASCII."""
    alvo = nome.casefold()
    for categoria in listar_categorias(db):
        if categoria.id != ignorar_id and categoria.nome.casefold() == alvo:
            return categoria
    return None


def criar_categoria(db: Session, nome: str) -> Categoria:
    existente = _categoria_com_nome(db, nome)
    if existente is not None:
        raise CategoriaDuplicadaError(existente.nome)
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


def listar_materiais(
    db: Session,
    categoria_id: int | None = None,
    busca: str | None = None,
    status: str | None = None,
) -> list[Material]:
    consulta = (
        select(Material)
        .options(joinedload(Material.categoria))
        .where(Material.excluido_em.is_(None))
        .order_by(Material.nome)
    )
    if categoria_id is not None:
        if db.get(Categoria, categoria_id) is None:
            raise CategoriaInexistenteError(categoria_id)
        consulta = consulta.where(Material.categoria_id == categoria_id)
    if busca and busca.strip():
        termo = busca.strip().lower()
        consulta = consulta.where(
            func.lower(Material.nome).contains(termo, autoescape=True)
        )
    if status == STATUS_INDISPONIVEL:
        consulta = consulta.where(Material.quantidade == 0)
    elif status == STATUS_DISPONIVEL:
        consulta = consulta.where(Material.quantidade > 0)
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
        .where(Material.id == material_id, Material.excluido_em.is_(None))
        .execution_options(populate_existing=True)
    )
    material = db.scalar(consulta)
    if material is None:
        raise MaterialInexistenteError(material_id)
    return material


def excluir_material(db: Session, material_id: int, confirmar: bool = False) -> None:
    """Exclusão **lógica**: marca o material como excluído e o registro continua
    no banco, com as suas movimentações. Com saldo maior que zero, só exclui com
    `confirmar` (CA-12); sem ela, informa o saldo e não grava."""
    material = obter_material(db, material_id)
    if material.quantidade > 0 and not confirmar:
        raise ConfirmacaoDeExclusaoError(material.nome, material.quantidade)
    material.excluido_em = datetime.now(UTC)
    db.commit()


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
        .where(Material.id == material_id, Material.excluido_em.is_(None))
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
        .where(
            Material.id == material_id,
            Material.excluido_em.is_(None),
            Material.quantidade >= quantidade,
        )
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
    existentes = {c.nome.casefold() for c in listar_categorias(db)}
    for nome in CATEGORIAS_INICIAIS:
        if nome.casefold() not in existentes:
            db.add(Categoria(nome=nome))
    db.commit()
