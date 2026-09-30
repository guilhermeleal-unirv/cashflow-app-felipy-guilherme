from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from datetime import date
from sqlmodel import select
from integration.database import SessionDep
from models.financeiro import RegistroFinanceiro, RegistroFinanceiroRead, Parcela, ParcelaRead, DepositoBaixa

registro_router = APIRouter(prefix="/registros", tags=["Registros Financeiros e Parcelas"])

class NovaBaixaPayload(BaseModel):
    data_deposito: date
    valor_depositado: float
    comprovante: str | None = None

# ===============================================
# Registros
# ===============================================
@registro_router.get("/", response_model=list[RegistroFinanceiroRead])
def listar_registros(session: SessionDep, skip: int = 0, limit: int = 100):
    registros = session.exec(select(RegistroFinanceiro).offset(skip).limit(limit)).all()
    return registros

@registro_router.get("/{registro_id}", response_model=RegistroFinanceiroRead)
def ler_registro(registro_id: int, session: SessionDep):
    registro = session.get(RegistroFinanceiro, registro_id)
    if not registro:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    return registro

# ===============================================
# Parcelas e Baixas
# ===============================================
@registro_router.get("/parcelas/{parcela_id}", response_model=ParcelaRead)
def ler_parcela(parcela_id: int, session: SessionDep):
    parcela = session.get(Parcela, parcela_id)
    if not parcela:
        raise HTTPException(status_code=404, detail="Parcela não encontrada")
    return parcela

@registro_router.post("/parcelas/{parcela_id}/baixa")
def registrar_baixa_parcela(
    parcela_id: int,
    payload: NovaBaixaPayload,
    session: SessionDep
):
    parcela = session.get(Parcela, parcela_id)
    if not parcela:
        raise HTTPException(status_code=404, detail="Parcela não encontrada")
        
    if parcela.status == "Liquidada":
        raise HTTPException(status_code=400, detail="Esta parcela já está totalmente liquidada")
        
    # Salvar o depósito parcial
    nova_baixa = DepositoBaixa(
        data_deposito=payload.data_deposito,
        valor_depositado=payload.valor_depositado,
        comprovante=payload.comprovante,
        parcela_id=parcela.id
    )
    session.add(nova_baixa)
    session.commit()
    
    # Calcular se o valor total das baixas já quitou a parcela
    session.refresh(parcela) # Recarregar para trazer a nova baixa
    total_baixado = sum(b.valor_depositado for b in parcela.depositos)
    
    # Tolerância pequena para lidar com floating points
    if total_baixado >= parcela.valor_parcela - 0.01:
        parcela.status = "Liquidada"
        session.add(parcela)
        session.commit()
        return {"message": "Baixa registrada com sucesso. A Parcela foi Liquidada!"}
        
    return {
        "message": f"Baixa parcial registrada. Faltam {parcela.valor_parcela - total_baixado:.2f} para liquidar.",
        "status_atual": parcela.status
    }
