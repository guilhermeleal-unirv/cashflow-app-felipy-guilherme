from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from datetime import date
from sqlmodel import select, delete
from integration.database import SessionDep
from models.financeiro import (
    RegistroFinanceiro, Parcela, ParcelaRead, DepositoBaixa, Parceiro, Titular,
    Categoria, RegistroCategoria, STATUS_ATIVO, STATUS_INATIVO,
)

registro_router = APIRouter(prefix="/registros", tags=["Registros Financeiros e Parcelas"])

class NovaBaixaPayload(BaseModel):
    data_deposito: date
    valor_depositado: float
    comprovante: str | None = None

class ParcelaIn(BaseModel):
    data_vencimento: date
    valor: float

class RegistroIn(BaseModel):
    """STATUS é oculto: não faz parte do payload."""
    tipo: str = "APAGAR"  # APAGAR | ARECEBER
    valor_total: float
    data_emissao: date
    titular_id: int | None = None
    parceiro_id: int | None = None
    categoria_ids: list[int] = []
    parcelas: list[ParcelaIn] = []

def _serializar(session, r: RegistroFinanceiro) -> dict:
    p = session.get(Parceiro, r.parceiro_id) if r.parceiro_id else None
    t = session.get(Titular, r.titular_id) if r.titular_id else None
    cat_ids = [rc.categoria_id for rc in session.exec(
        select(RegistroCategoria).where(RegistroCategoria.registro_id == r.id)).all()]
    if r.categoria_id and r.categoria_id not in cat_ids:
        cat_ids.insert(0, r.categoria_id)
    cats = [session.get(Categoria, i) for i in cat_ids]
    parcelas = session.exec(select(Parcela).where(Parcela.registro_id == r.id)
                            .order_by(Parcela.numero_parcela)).all()
    return {
        "id": r.id, "tipo": r.tipo, "status": r.status,
        "valor_total": r.valor_total, "data_emissao": r.data_emissao,
        "parceiro_id": r.parceiro_id, "parceiro": p.nome_razao if p else None,
        "titular_id": r.titular_id, "titular": t.nome if t else None,
        "categoria_ids": cat_ids,
        "categoria": ", ".join(c.nome for c in cats if c),
        "parcelas": [{"id": x.id, "numero_parcela": x.numero_parcela,
                      "data_vencimento": x.data_vencimento, "valor_parcela": x.valor_parcela,
                      "status": x.status} for x in parcelas],
        "proximo_vencimento": min((x.data_vencimento for x in parcelas), default=None),
    }

def _gravar_filhos(session, r: RegistroFinanceiro, dados: RegistroIn):
    session.exec(delete(RegistroCategoria).where(RegistroCategoria.registro_id == r.id))
    for cid in dados.categoria_ids:
        session.add(RegistroCategoria(registro_id=r.id, categoria_id=cid))
    r.categoria_id = dados.categoria_ids[0] if dados.categoria_ids else None
    session.add(r)

def _gravar_parcelas(session, r: RegistroFinanceiro, dados: RegistroIn):
    parcelas = dados.parcelas or [ParcelaIn(data_vencimento=dados.data_emissao, valor=dados.valor_total)]
    for i, p in enumerate(parcelas, start=1):
        session.add(Parcela(numero_parcela=i, data_vencimento=p.data_vencimento,
                            valor_parcela=p.valor, status="Pendente", registro_id=r.id))

# ===============================================
# Registros (Contas a Pagar / Receber)
# ===============================================
@registro_router.get("/")
def listar_registros(request: Request, session: SessionDep, skip: int = 0, limit: int = 500,
                     sort: str = "id", order: str = "asc"):
    qp = request.query_params
    query = select(RegistroFinanceiro)
    st = qp.get("status", STATUS_ATIVO)  # TODOS => ATIVO
    if st and st.upper() in (STATUS_ATIVO, STATUS_INATIVO):
        query = query.where(RegistroFinanceiro.status == st.upper())
    if qp.get("tipo"):
        query = query.where(RegistroFinanceiro.tipo == qp.get("tipo").upper())
    if qp.get("parceiro"):
        query = query.join(Parceiro, Parceiro.id == RegistroFinanceiro.parceiro_id) \
            .where(Parceiro.nome_razao.ilike(f"%{qp.get('parceiro').strip()}%"))
    if qp.get("titular"):
        query = query.join(Titular, Titular.id == RegistroFinanceiro.titular_id) \
            .where(Titular.nome.ilike(f"%{qp.get('titular').strip()}%"))
    if qp.get("valor_min"):
        query = query.where(RegistroFinanceiro.valor_total >= float(qp.get("valor_min")))
    if qp.get("valor_max"):
        query = query.where(RegistroFinanceiro.valor_total <= float(qp.get("valor_max")))
    if qp.get("data_ini"):
        query = query.where(RegistroFinanceiro.data_emissao >= date.fromisoformat(qp.get("data_ini")))
    if qp.get("data_fim"):
        query = query.where(RegistroFinanceiro.data_emissao <= date.fromisoformat(qp.get("data_fim")))
    col = getattr(RegistroFinanceiro, sort, None) or RegistroFinanceiro.id
    query = query.order_by(col.desc() if order.lower() == "desc" else col.asc())
    return [_serializar(session, r) for r in session.exec(query.offset(skip).limit(limit)).all()]

@registro_router.post("/", status_code=status.HTTP_201_CREATED)
def criar_registro(dados: RegistroIn, session: SessionDep):
    if abs(sum(p.valor for p in dados.parcelas) - dados.valor_total) > 0.01 and dados.parcelas:
        raise HTTPException(status_code=422, detail="A soma das parcelas difere do valor total")
    r = RegistroFinanceiro(
        tipo=dados.tipo.upper(), valor_total=dados.valor_total, data_emissao=dados.data_emissao,
        titular_id=dados.titular_id, parceiro_id=dados.parceiro_id, status=STATUS_ATIVO)  # STATUS oculto == ATIVO
    session.add(r); session.flush()
    _gravar_filhos(session, r, dados)
    _gravar_parcelas(session, r, dados)
    session.commit(); session.refresh(r)
    return _serializar(session, r)

@registro_router.put("/{registro_id}")
def atualizar_registro(registro_id: int, dados: RegistroIn, session: SessionDep):
    r = session.get(RegistroFinanceiro, registro_id)
    if not r:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    if dados.parcelas and abs(sum(p.valor for p in dados.parcelas) - dados.valor_total) > 0.01:
        raise HTTPException(status_code=422, detail="A soma das parcelas difere do valor total")
    # STATUS oculto: não é alterado no UPDATE
    r.tipo = dados.tipo.upper(); r.valor_total = dados.valor_total
    r.data_emissao = dados.data_emissao
    r.titular_id = dados.titular_id; r.parceiro_id = dados.parceiro_id
    _gravar_filhos(session, r, dados)
    if dados.parcelas:
        atuais = session.exec(select(Parcela).where(Parcela.registro_id == r.id)).all()
        for p in atuais:
            if session.exec(select(DepositoBaixa).where(DepositoBaixa.parcela_id == p.id)).first():
                session.rollback()
                raise HTTPException(status_code=400, detail="Há parcelas com baixa registrada; não é possível reescrevê-las")
        for p in atuais:
            session.delete(p)
        session.flush()
        _gravar_parcelas(session, r, dados)
    session.commit(); session.refresh(r)
    return _serializar(session, r)

@registro_router.delete("/{registro_id}")
def excluir_registro(registro_id: int, session: SessionDep):
    r = session.get(RegistroFinanceiro, registro_id)
    if not r:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    r.status = STATUS_INATIVO  # exclusão lógica
    session.add(r); session.commit()
    return {"ok": True, "message": "Registro inativado com sucesso"}

@registro_router.patch("/{registro_id}/reativar")
def reativar_registro(registro_id: int, session: SessionDep):
    r = session.get(RegistroFinanceiro, registro_id)
    if not r:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    r.status = STATUS_ATIVO
    session.add(r); session.commit(); session.refresh(r)
    return _serializar(session, r)

@registro_router.get("/{registro_id}")
def ler_registro(registro_id: int, session: SessionDep):
    registro = session.get(RegistroFinanceiro, registro_id)
    if not registro:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    return _serializar(session, registro)

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
