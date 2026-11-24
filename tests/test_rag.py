import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from main import app
from integration.database import get_session
from models.user import User
from auth.dependencies import get_current_user
from auth.security import get_password_hash
from models.financeiro import (
    Parceiro, Titular, Categoria, RegistroFinanceiro, Parcela, STATUS_ATIVO
)
from services.agent_rag import AgentRAG, _cosine_similarity


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)

    # Cria o usuário padrão no banco do teste
    with Session(engine) as s:
        s.add(User(
            username="joao.paraiba",
            email="joao.paraiba@cashflow.com",
            hashed_password=get_password_hash("costelaoNoDomingo"),
            is_active=True
        ))
        # Adiciona registros de teste para o RAG
        p1 = Parceiro(nome_razao="IGUAÇU MÁQUINAS AGRÍCOLAS", cnpj_cpf="11111111000100", tipo="FORNECEDOR")
        p2 = Parceiro(nome_razao="COOPERATIVA AGRO RURAL", cnpj_cpf="22222222000100", tipo="FORNECEDOR")
        t1 = Titular(nome="BELTRANO DA SILVA", cpf_cnpj="99999999999")
        c1 = Categoria(nome="MANUTENÇÃO E OPERAÇÃO", tipo="DESPESA")
        c2 = Categoria(nome="INSUMOS AGRÍCOLAS", tipo="DESPESA")
        s.add_all([p1, p2, t1, c1, c2])
        s.commit()

        # Registro 1: Manutenção de trator
        r1 = RegistroFinanceiro(
            valor_total=1500.0,
            data_emissao=date(2026, 10, 15),
            tipo="APAGAR",
            status=STATUS_ATIVO,
            titular_id=t1.id,
            parceiro_id=p1.id,
            categoria_id=c1.id
        )
        s.add(r1)
        s.commit()
        s.refresh(r1)

        parc1 = Parcela(numero_parcela=1, data_vencimento=date(2026, 11, 15), valor_parcela=1500.0, status="Pendente", registro_id=r1.id)
        s.add(parc1)

        # Registro 2: Adubo e sementes
        r2 = RegistroFinanceiro(
            valor_total=3200.0,
            data_emissao=date(2026, 10, 20),
            tipo="APAGAR",
            status=STATUS_ATIVO,
            titular_id=t1.id,
            parceiro_id=p2.id,
            categoria_id=c2.id
        )
        s.add(r2)
        s.commit()
        s.refresh(r2)

        parc2 = Parcela(numero_parcela=1, data_vencimento=date(2026, 12, 1), valor_parcela=3200.0, status="Pendente", registro_id=r2.id)
        s.add(parc2)
        s.commit()

    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    app.dependency_overrides[get_current_user] = lambda: User(username="joao.paraiba", id=1)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_cosine_similarity():
    # Vetores idênticos têm similaridade 1.0
    v1 = [1.0, 0.0, 1.0]
    assert pytest.approx(_cosine_similarity(v1, v1), 0.001) == 1.0

    # Vetores ortogonais têm similaridade 0.0
    v2 = [0.0, 1.0, 0.0]
    assert _cosine_similarity(v1, v2) == 0.0

    # Vetores vazios
    assert _cosine_similarity([], []) == 0.0


def test_rag_status_endpoint(client):
    r = client.get("/rag/status")
    assert r.status_code == 200
    dados = r.json()
    assert dados["total_registros_ativos"] >= 2
    assert dados["total_parceiros_ativos"] >= 2
    assert "status" in dados


def test_rag_consultar_simples(client):
    body = {
        "query": "Quais são as contas a pagar para a Iguaçu Máquinas?",
        "modo": "simples"
    }
    r = client.post("/rag/consultar", json=body)
    assert r.status_code == 200
    dados = r.json()
    assert dados["modo"] == "simples"
    assert "resposta" in dados
    assert "fontes" in dados
    assert dados["total_fontes"] >= 2
    # Verifica que os dados da Iguaçu Máquinas foram recuperados
    nomes_fontes = [f.get("parceiro") for f in dados["fontes"]]
    assert any("IGUAÇU" in str(n) for n in nomes_fontes)


def test_rag_consultar_embeddings_semantico(client):
    body = {
        "query": "Qual o valor gasto com manutenção de peças e trator?",
        "modo": "embeddings",
        "top_k": 2
    }
    r = client.post("/rag/consultar", json=body)
    assert r.status_code == 200
    dados = r.json()
    assert dados["modo"] == "embeddings"
    assert "resposta" in dados
    assert "fontes" in dados
    assert len(dados["fontes"]) <= 2
    # Verifica que há score de similaridade
    primeiro = dados["fontes"][0]
    assert "similaridade_score" in primeiro
    assert "texto_semantico" in primeiro


def test_rag_consultar_modo_ambos(client):
    body = {
        "query": "Qual fornecedor tem conta vencendo em novembro?",
        "modo": "ambos"
    }
    r = client.post("/rag/consultar", json=body)
    assert r.status_code == 200
    dados = r.json()
    assert dados["modo"] == "ambos"
    assert "simples" in dados
    assert "embeddings" in dados
    assert "resposta" in dados["simples"]
    assert "resposta" in dados["embeddings"]


def test_rag_validacoes(client):
    # Pergunta vazia deve retornar 400
    r_vazia = client.post("/rag/consultar", json={"query": "   ", "modo": "simples"})
    assert r_vazia.status_code == 400

    # Reindexar cache
    r_reindex = client.post("/rag/reindexar")
    assert r_reindex.status_code == 200
    assert "total_indexados" in r_reindex.json()
