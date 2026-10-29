from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Categoria(Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True)


class Material(Base):
    __tablename__ = "materiais"
    __table_args__ = (
        CheckConstraint("quantidade >= 0", name="ck_material_quantidade"),
        CheckConstraint("estoque_minimo >= 0", name="ck_material_estoque_minimo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(150))
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias.id"))
    quantidade: Mapped[int] = mapped_column(default=0)
    estoque_minimo: Mapped[int] = mapped_column(default=0)
    # Exclusão lógica: data e hora (UTC) da exclusão; vazia = material ativo.
    excluido_em: Mapped[datetime | None] = mapped_column(default=None)

    categoria: Mapped[Categoria] = relationship()


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint(
            "perfil IN ('administrador', 'estoquista', 'operador')",
            name="ck_usuario_perfil",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(150))
    cpf: Mapped[str] = mapped_column(String(11), unique=True)
    email: Mapped[str] = mapped_column(String(254))
    perfil: Mapped[str] = mapped_column(String(20))
    senha_hash: Mapped[str] = mapped_column(String(200))
    ativo: Mapped[bool] = mapped_column(default=True)


class Movimentacao(Base):
    __tablename__ = "movimentacoes"
    __table_args__ = (
        CheckConstraint("tipo IN ('entrada', 'saida')", name="ck_mov_tipo"),
        CheckConstraint("quantidade > 0", name="ck_mov_quantidade"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materiais.id"))
    tipo: Mapped[str] = mapped_column(String(10))
    quantidade: Mapped[int]
    saldo_apos: Mapped[int]
    data: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
