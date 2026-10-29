"""Atualização leve de bancos criados por versões anteriores do sistema.

`create_all` cria tabelas que faltam, mas não acrescenta colunas a tabelas que já
existem. Esta migração só **adiciona** colunas vazias (`ALTER TABLE ... ADD COLUMN`),
nunca altera nem apaga dados, e pode rodar quantas vezes for preciso: antes de
cada passo ela confere se a coluna já existe.
"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

COLUNAS_NOVAS = (
    # (tabela, coluna, tipo SQL)
    ("materiais", "excluido_em", "DATETIME"),
)


def _colunas_da_tabela(engine: Engine, tabela: str) -> set[str]:
    return {coluna["name"] for coluna in inspect(engine).get_columns(tabela)}


def migrar(engine: Engine) -> list[str]:
    """Aplica as colunas que faltam e devolve a lista do que foi acrescentado."""
    aplicadas: list[str] = []
    for tabela, coluna, tipo in COLUNAS_NOVAS:
        if coluna in _colunas_da_tabela(engine, tabela):
            continue
        with engine.begin() as conexao:
            conexao.execute(text(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}"))
        aplicadas.append(f"{tabela}.{coluna}")
    return aplicadas
