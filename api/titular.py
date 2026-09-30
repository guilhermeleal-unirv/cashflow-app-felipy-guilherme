from fastapi import APIRouter, HTTPException, status
from sqlmodel import select
from integration.database import SessionDep
from models.financeiro import Titular, TitularCreate, TitularRead

titular_router = APIRouter(prefix="/titulares", tags=["Titulares"])

@titular_router.post("/", response_model=TitularRead, status_code=status.HTTP_201_CREATED)
def create_titular(*, session: SessionDep, titular: TitularCreate):
    db_titular = Titular.model_validate(titular)
    session.add(db_titular)
    session.commit()
    session.refresh(db_titular)
    return db_titular

@titular_router.get("/", response_model=list[TitularRead])
def read_titulares(session: SessionDep, skip: int = 0, limit: int = 100):
    titulares = session.exec(select(Titular).offset(skip).limit(limit)).all()
    return titulares

@titular_router.get("/{titular_id}", response_model=TitularRead)
def read_titular(*, session: SessionDep, titular_id: int):
    titular = session.get(Titular, titular_id)
    if not titular:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Titular não encontrado")
    return titular

@titular_router.delete("/{titular_id}")
def delete_titular(*, session: SessionDep, titular_id: int):
    titular = session.get(Titular, titular_id)
    if not titular:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Titular não encontrado")
    session.delete(titular)
    session.commit()
    return {"ok": True, "message": "Titular deletado com sucesso"}
