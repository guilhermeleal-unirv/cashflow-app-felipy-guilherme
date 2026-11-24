"""
Módulo de rotas da API para Consulta com Agente Inteligente RAG (N3).
Disponibiliza endpoints para:
- Consulta via RAG Simples (SQL tabular direto)
- Consulta via RAG Embeddings (Busca semântica por similaridade de cosseno)
- Modo comparativo ('ambos')
- Status da base de conhecimento do RAG
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlmodel import select, func

from integration.database import SessionDep
from services.agent_rag import AgentRAG, _EMBEDDINGS_CACHE
from models.financeiro import RegistroFinanceiro, Parceiro, Titular, Categoria, STATUS_ATIVO

rag_router = APIRouter(prefix="/rag", tags=["Consulta Inteligente (RAG)"])


class RAGQueryPayload(BaseModel):
    query: str = Field(..., description="Pergunta do usuário sobre o banco de dados financeiro")
    modo: str = Field(default="simples", description="Modo de RAG: 'simples', 'embeddings' ou 'ambos'")
    top_k: int = Field(default=5, ge=1, le=20, description="Quantidade de documentos mais relevantes no modo embeddings")
    api_key: Optional[str] = Field(default=None, description="Gemini API Key opcional enviada pelo frontend")


class RAGStatusResponse(BaseModel):
    total_registros_ativos: int
    total_parceiros_ativos: int
    total_titulares_ativos: int
    total_categorias_ativas: int
    embeddings_em_cache: int
    status: str


@rag_router.post("/consultar")
def consultar_rag(payload: RAGQueryPayload, session: SessionDep):
    """
    Endpoint principal da N3:
    Executa a consulta RAG com agente inteligente usando RAG Simples ou RAG Embeddings.
    """
    if not payload.query or not payload.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A pergunta não pode estar vazia."
        )

    try:
        agent = AgentRAG(api_key=payload.api_key)
        resultado = agent.consultar(
            session=session,
            query=payload.query,
            modo=payload.modo,
            top_k=payload.top_k,
            api_key=payload.api_key
        )
        return resultado
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar consulta RAG: {str(e)}"
        )


@rag_router.get("/status", response_model=RAGStatusResponse)
def status_rag(session: SessionDep):
    """Retorna estatísticas da base de dados e do cache vetorial do RAG."""
    total_reg = session.exec(
        select(func.count(RegistroFinanceiro.id)).where(RegistroFinanceiro.status == STATUS_ATIVO)
    ).one()
    total_parc = session.exec(
        select(func.count(Parceiro.id)).where(Parceiro.status == STATUS_ATIVO)
    ).one()
    total_tit = session.exec(
        select(func.count(Titular.id)).where(Titular.status == STATUS_ATIVO)
    ).one()
    total_cat = session.exec(
        select(func.count(Categoria.id)).where(Categoria.status == STATUS_ATIVO)
    ).one()

    return RAGStatusResponse(
        total_registros_ativos=total_reg,
        total_parceiros_ativos=total_parc,
        total_titulares_ativos=total_tit,
        total_categorias_ativas=total_cat,
        embeddings_em_cache=len(_EMBEDDINGS_CACHE),
        status="Pronto para consultas"
    )


@rag_router.post("/reindexar")
def reindexar_embeddings(session: SessionDep, api_key: Optional[str] = None):
    """Limpa o cache vetorial e reindexa os embeddings dos registros ativos."""
    _EMBEDDINGS_CACHE.clear()
    agent = AgentRAG(api_key=api_key)
    # Pré-carrega e aquece o cache
    docs = agent._carregar_registros_completos(session)
    for d in docs:
        cache_key = f"doc_{d['id']}_{d['valor_total']}_{d['categoria']}"
        _EMBEDDINGS_CACHE[cache_key] = agent._gerar_embedding(d["texto_semantico"], api_key=api_key)

    return {
        "message": f"Cache vetorial reindexado com sucesso. {len(_EMBEDDINGS_CACHE)} registros vetorizados.",
        "total_indexados": len(_EMBEDDINGS_CACHE)
    }
