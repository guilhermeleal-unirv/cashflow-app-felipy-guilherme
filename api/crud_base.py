"""
Fábrica de rotas CRUD com exclusão lógica (STATUS ATIVO/INATIVO).

Regras (recomendações de layout da N2):
- CREATE: o campo STATUS é oculto e sempre gravado como ATIVO.
- UPDATE: o campo STATUS é oculto e nunca é alterado.
- DELETE: não apaga; altera STATUS para INATIVO.
- Reativar: altera STATUS para ATIVO.
- Listagem: filtros combinados (AND), por texto parcial ou valor exato, ordenação por coluna.
"""
import re
from fastapi import APIRouter, HTTPException, Request, status
from sqlmodel import select
from integration.database import SessionDep
from models.financeiro import STATUS_ATIVO, STATUS_INATIVO


def somente_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def make_crud_router(*, prefix, tag, Model, Create, Update, Read,
                     text_filters, exact_filters=(), digit_filters=None, rotulo="Registro"):
    """
    text_filters:  {param_url: nome_coluna}  -> LIKE %valor% (case-insensitive)
    exact_filters: nomes de colunas comparadas por igualdade (ex.: tipo)
    digit_filters: {param_url: nome_coluna} comparados apenas por dígitos
    """
    digit_filters = digit_filters or {}
    digit_cols = set(digit_filters.values())
    router = APIRouter(prefix=prefix, tags=[tag])

    def _normalizar(obj):
        # Documentos (CPF/CNPJ) são armazenados apenas com dígitos
        for col in digit_cols:
            setattr(obj, col, somente_digitos(getattr(obj, col)))
        if getattr(obj, "tipo", None):
            obj.tipo = obj.tipo.upper()

    @router.get("/", response_model=list[Read])
    def listar(request: Request, session: SessionDep, skip: int = 0, limit: int = 500,
               sort: str = "id", order: str = "asc"):
        qp = request.query_params
        query = select(Model)
        # TODOS => status=ATIVO (padrão); status=TODOS inclui inativos
        st = qp.get("status", STATUS_ATIVO)
        if st and st.upper() in (STATUS_ATIVO, STATUS_INATIVO):
            query = query.where(Model.status == st.upper())
        for param, coluna in text_filters.items():
            if qp.get(param):
                query = query.where(getattr(Model, coluna).ilike(f"%{qp.get(param).strip()}%"))
        for param, coluna in digit_filters.items():
            if qp.get(param):
                query = query.where(getattr(Model, coluna).contains(somente_digitos(qp.get(param)) or qp.get(param)))
        for coluna in exact_filters:
            if qp.get(coluna):
                query = query.where(getattr(Model, coluna) == qp.get(coluna).upper())
        col = getattr(Model, sort, None) or Model.id
        query = query.order_by(col.desc() if order.lower() == "desc" else col.asc())
        return session.exec(query.offset(skip).limit(limit)).all()

    @router.post("/", response_model=Read, status_code=status.HTTP_201_CREATED)
    def criar(*, session: SessionDep, dados: Create):
        obj = Model.model_validate(dados, update={"status": STATUS_ATIVO})
        _normalizar(obj)
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj

    @router.get("/{item_id}", response_model=Read)
    def ler(*, session: SessionDep, item_id: int):
        obj = session.get(Model, item_id)
        if not obj:
            raise HTTPException(status_code=404, detail=f"{rotulo} não encontrado")
        return obj

    @router.put("/{item_id}", response_model=Read)
    def atualizar(*, session: SessionDep, item_id: int, dados: Update):
        obj = session.get(Model, item_id)
        if not obj:
            raise HTTPException(status_code=404, detail=f"{rotulo} não encontrado")
        # STATUS não faz parte do schema de update => nunca é alterado aqui
        for k, v in dados.model_dump(exclude_unset=True, exclude_none=True).items():
            setattr(obj, k, v)
        _normalizar(obj)
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj

    @router.delete("/{item_id}")
    def excluir_logico(*, session: SessionDep, item_id: int):
        obj = session.get(Model, item_id)
        if not obj:
            raise HTTPException(status_code=404, detail=f"{rotulo} não encontrado")
        obj.status = STATUS_INATIVO
        session.add(obj)
        session.commit()
        return {"ok": True, "message": f"{rotulo} inativado com sucesso"}

    @router.patch("/{item_id}/reativar", response_model=Read)
    def reativar(*, session: SessionDep, item_id: int):
        obj = session.get(Model, item_id)
        if not obj:
            raise HTTPException(status_code=404, detail=f"{rotulo} não encontrado")
        obj.status = STATUS_ATIVO
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj

    return router
