"""
Módulo de configuração do banco de dados utilizando SQLModel e SQLAlchemy.
Lida com a conexão, criação das tabelas e injeção de dependência da sessão.
"""
import os
from contextlib import asynccontextmanager
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from sqlmodel import Session, SQLModel, create_engine

# Importamos os modelos para que as tabelas sejam criadas corretamente
import models

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    from integration.migrations import run_migrations
    run_migrations(engine)

def get_session():
    with Session(engine) as session:
        yield session

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Criando tabelas no banco de dados...")
    create_db_and_tables()
    yield

SessionDep = Annotated[Session, Depends(get_session)]
