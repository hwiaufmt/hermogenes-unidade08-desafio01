import os
import secrets

# Chave que assina o cookie de sessão. Em produção, defina ESTOQUE_SECRET_KEY:
# sem ela, uma chave aleatória é gerada a cada início e as sessões não sobrevivem
# a reinicializações.
CHAVE_SECRETA = os.environ.get("ESTOQUE_SECRET_KEY") or secrets.token_urlsafe(32)

DURACAO_SESSAO_SEGUNDOS = 8 * 60 * 60

# Primeiro administrador: criado no início, só se ainda não houver nenhum
# usuário. Defina ESTOQUE_ADMIN_CPF e ESTOQUE_ADMIN_SENHA para usar.
ADMIN_CPF = os.environ.get("ESTOQUE_ADMIN_CPF", "")
ADMIN_SENHA = os.environ.get("ESTOQUE_ADMIN_SENHA", "")
ADMIN_NOME = os.environ.get("ESTOQUE_ADMIN_NOME", "Administrador")
ADMIN_EMAIL = os.environ.get("ESTOQUE_ADMIN_EMAIL", "administrador@estoque.local")
