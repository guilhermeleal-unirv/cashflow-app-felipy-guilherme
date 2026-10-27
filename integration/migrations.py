"""
Migração leve e idempotente: adiciona colunas novas em tabelas já existentes
(SQLModel.create_all não altera tabelas criadas anteriormente).
"""
from sqlalchemy import inspect, text

# (tabela, coluna, DDL do tipo/default)
_COLUNAS = [
    ("titular", "status", "VARCHAR DEFAULT 'ATIVO'"),
    ("parceiro", "status", "VARCHAR DEFAULT 'ATIVO'"),
    ("categoria", "status", "VARCHAR DEFAULT 'ATIVO'"),
    ("registrofinanceiro", "status", "VARCHAR DEFAULT 'ATIVO'"),
    ("registrofinanceiro", "tipo", "VARCHAR DEFAULT 'APAGAR'"),
]


def run_migrations(engine):
    insp = inspect(engine)
    tabelas = insp.get_table_names()
    with engine.begin() as conn:
        for tabela, coluna, ddl in _COLUNAS:
            if tabela not in tabelas:
                continue
            existentes = {c["name"] for c in insp.get_columns(tabela)}
            if coluna not in existentes:
                conn.execute(text(f'ALTER TABLE {tabela} ADD COLUMN {coluna} {ddl}'))
            conn.execute(text(f"UPDATE {tabela} SET {coluna} = {ddl.split('DEFAULT ')[1]} WHERE {coluna} IS NULL"))
