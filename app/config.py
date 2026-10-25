import os
import secrets

# Chave que assina o cookie de sessão. Em produção, defina ESTOQUE_SECRET_KEY:
# sem ela, uma chave aleatória é gerada a cada início e as sessões não sobrevivem
# a reinicializações.
CHAVE_SECRETA = os.environ.get("ESTOQUE_SECRET_KEY") or secrets.token_urlsafe(32)

DURACAO_SESSAO_SEGUNDOS = 8 * 60 * 60

# PROTÓTIPO: senha usada quando um usuário é cadastrado sem informar senha, e
# senha do administrador inicial. Troque antes de qualquer uso real.
SENHA_PADRAO = "123456"

# Primeiro administrador: criado no início, só se ainda não houver nenhum
# usuário. Sem as variáveis de ambiente, usa o administrador padrão do protótipo
# (CPF de exemplo com dígitos válidos e a senha padrão).
ADMIN_CPF = os.environ.get("ESTOQUE_ADMIN_CPF") or "529.982.247-25"
ADMIN_SENHA = os.environ.get("ESTOQUE_ADMIN_SENHA") or SENHA_PADRAO
ADMIN_NOME = os.environ.get("ESTOQUE_ADMIN_NOME", "Administrador")
ADMIN_EMAIL = os.environ.get("ESTOQUE_ADMIN_EMAIL", "administrador@estoque.local")
