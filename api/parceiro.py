from fastapi import APIRouter, HTTPException, status
from sqlmodel import select
from integration.database import SessionDep
from models.financeiro import Parceiro, ParceiroCreate, ParceiroRead

parceiro_router = APIRouter(prefix="/parceiros", tags=["Parceiros"])

@parceiro_router.post("/", response_model=ParceiroRead, status_code=status.HTTP_201_CREATED)
def create_parceiro(*, session: SessionDep, parceiro: ParceiroCreate):
    db_parceiro = Parceiro.model_validate(parceiro)
    session.add(db_parceiro)
    session.commit()
    session.refresh(db_parceiro)
    return db_parceiro

@parceiro_router.get("/", response_model=list[ParceiroRead])
def read_parceiros(session: SessionDep, skip: int = 0, limit: int = 100):
    parceiros = session.exec(select(Parceiro).offset(skip).limit(limit)).all()
    return parceiros

@parceiro_router.get("/{parceiro_id}", response_model=ParceiroRead)
def read_parceiro(*, session: SessionDep, parceiro_id: int):
    parceiro = session.get(Parceiro, parceiro_id)
    if not parceiro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parceiro não encontrado")
    return parceiro

@parceiro_router.delete("/{parceiro_id}")
def delete_parceiro(*, session: SessionDep, parceiro_id: int):
    parceiro = session.get(Parceiro, parceiro_id)
    if not parceiro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parceiro não encontrado")
    session.delete(parceiro)
    session.commit()
    return {"ok": True, "message": "Parceiro deletado com sucesso"}
