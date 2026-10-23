import re

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Usuario
from app.seguranca import gerar_hash

PERFIL_ADMINISTRADOR = "administrador"
PERFIL_ESTOQUISTA = "estoquista"
PERFIL_OPERADOR = "operador"
PERFIS = (PERFIL_ADMINISTRADOR, PERFIL_ESTOQUISTA, PERFIL_OPERADOR)
TAMANHO_MINIMO_SENHA = 8
_PADRAO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UsuarioInexistenteError(Exception):
    def __init__(self, usuario_id: int) -> None:
        super().__init__(f"O usuário {usuario_id} não existe.")


class CpfDuplicadoError(Exception):
    def __init__(self, cpf: str) -> None:
        super().__init__(f"Já existe um usuário com o CPF {formatar_cpf(cpf)}.")


class UltimoAdministradorError(Exception):
    def __init__(self) -> None:
        super().__init__(
            "Não é possível inativar ou alterar o perfil do último administrador ativo."
        )


def normalizar_cpf(cpf: str) -> str:
    return re.sub(r"\D", "", cpf)


def formatar_cpf(cpf: str) -> str:
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


def _digito_verificador(base: str) -> int:
    pesos = range(len(base) + 1, 1, -1)
    resto = sum(int(d) * p for d, p in zip(base, pesos, strict=True)) * 10 % 11
    return 0 if resto == 10 else resto


def cpf_valido(cpf: str) -> bool:
    if len(cpf) != 11 or not cpf.isdigit() or len(set(cpf)) == 1:
        return False
    primeiro = _digito_verificador(cpf[:9])
    segundo = _digito_verificador(cpf[:9] + str(primeiro))
    return cpf[9:] == f"{primeiro}{segundo}"


def email_valido(email: str) -> bool:
    return bool(_PADRAO_EMAIL.match(email))


def listar_usuarios(db: Session) -> list[Usuario]:
    return list(db.scalars(select(Usuario).order_by(Usuario.nome)))


def obter_usuario(db: Session, usuario_id: int) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise UsuarioInexistenteError(usuario_id)
    return usuario


def criar_usuario(
    db: Session, nome: str, cpf: str, email: str, perfil: str, senha: str
) -> Usuario:
    usuario = Usuario(
        nome=nome,
        cpf=cpf,
        email=email,
        perfil=perfil,
        senha_hash=gerar_hash(senha),
    )
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise CpfDuplicadoError(cpf) from None
    return usuario


def _garantir_outro_administrador(db: Session, usuario: Usuario) -> None:
    if usuario.perfil != PERFIL_ADMINISTRADOR or not usuario.ativo:
        return
    ativos = db.scalar(
        select(func.count())
        .select_from(Usuario)
        .where(Usuario.perfil == PERFIL_ADMINISTRADOR, Usuario.ativo.is_(True))
    )
    if ativos <= 1:
        raise UltimoAdministradorError()


def atualizar_usuario(
    db: Session,
    usuario_id: int,
    nome: str,
    email: str,
    perfil: str,
    senha: str | None = None,
) -> Usuario:
    usuario = obter_usuario(db, usuario_id)
    if perfil != usuario.perfil:
        _garantir_outro_administrador(db, usuario)
    usuario.nome = nome
    usuario.email = email
    usuario.perfil = perfil
    if senha is not None:
        usuario.senha_hash = gerar_hash(senha)
    db.commit()
    return usuario


def inativar_usuario(db: Session, usuario_id: int) -> Usuario:
    usuario = obter_usuario(db, usuario_id)
    _garantir_outro_administrador(db, usuario)
    usuario.ativo = False
    db.commit()
    return usuario


def reativar_usuario(db: Session, usuario_id: int) -> Usuario:
    usuario = obter_usuario(db, usuario_id)
    usuario.ativo = True
    db.commit()
    return usuario
