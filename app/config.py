import os
import secrets

# Chave que assina o cookie de sessão. Em produção, defina ESTOQUE_SECRET_KEY:
# sem ela, uma chave aleatória é gerada a cada início e as sessões não sobrevivem
# a reinicializações.
CHAVE_SECRETA = os.environ.get("ESTOQUE_SECRET_KEY") or secrets.token_urlsafe(32)

DURACAO_SESSAO_SEGUNDOS = 8 * 60 * 60
