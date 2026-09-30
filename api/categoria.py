from fastapi import APIRouter, HTTPException, status
from sqlmodel import select
from integration.database import SessionDep
from models.financeiro import Categoria, CategoriaCreate, CategoriaRead

categoria_router = APIRouter(prefix="/categorias", tags=["Categorias"])

@categoria_router.post("/", response_model=CategoriaRead, status_code=status.HTTP_201_CREATED)
def create_categoria(*, session: SessionDep, categoria: CategoriaCreate):
    db_categoria = Categoria.model_validate(categoria)
    session.add(db_categoria)
    session.commit()
    session.refresh(db_categoria)
    return db_categoria

@categoria_router.get("/", response_model=list[CategoriaRead])
def read_categorias(session: SessionDep, skip: int = 0, limit: int = 100):
    categorias = session.exec(select(Categoria).offset(skip).limit(limit)).all()
    return categorias

@categoria_router.get("/{categoria_id}", response_model=CategoriaRead)
def read_categoria(*, session: SessionDep, categoria_id: int):
    categoria = session.get(Categoria, categoria_id)
    if not categoria:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria não encontrada")
    return categoria

@categoria_router.delete("/{categoria_id}")
def delete_categoria(*, session: SessionDep, categoria_id: int):
    categoria = session.get(Categoria, categoria_id)
    if not categoria:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria não encontrada")
    session.delete(categoria)
    session.commit()
    return {"ok": True, "message": "Categoria deletada com sucesso"}
