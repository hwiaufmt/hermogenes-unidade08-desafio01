import hashlib
import hmac
import secrets

_N, _R, _P = 2**14, 8, 1
_TAMANHO_SAL = 16


def gerar_hash(senha: str) -> str:
    sal = secrets.token_bytes(_TAMANHO_SAL)
    derivado = hashlib.scrypt(senha.encode(), salt=sal, n=_N, r=_R, p=_P)
    return f"scrypt${_N}${_R}${_P}${sal.hex()}${derivado.hex()}"


def verificar_senha(senha: str, hash_guardado: str) -> bool:
    try:
        _, n, r, p, sal, esperado = hash_guardado.split("$")
        derivado = hashlib.scrypt(
            senha.encode(), salt=bytes.fromhex(sal), n=int(n), r=int(r), p=int(p)
        )
    except ValueError:
        return False
    return hmac.compare_digest(derivado, bytes.fromhex(esperado))
