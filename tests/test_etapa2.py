import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from main import app
from integration.database import get_session


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)

    def override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app)  # sem 'with' => não dispara o lifespan (Postgres)
    app.dependency_overrides.clear()


DANFE = {
    "emitente": {"razao_social": "IGUAÇU MAQUINAS LTDA", "cnpj": "11111111000100"},
    "destinatario": {"nome_razao": "BELTRANO DA SILVA", "cnpj_cpf": "99999999999"},
    "nota_fiscal": {"data_emissao": "2026-10-01"},
    "totais": {"valor_total_nota": 300.0},
    "parcelas": [
        {"numero": 1, "data_vencimento": "2026-11-01", "valor": 100.0},
        {"numero": 2, "data_vencimento": "2026-12-01", "valor": 200.0},
    ],
    "classificacao_despesa": "MANUTENÇÃO E OPERAÇÃO",
}


@pytest.mark.parametrize("url,body", [
    ("/parceiros/", {"nome_razao": "ACME", "cnpj_cpf": "123", "tipo": "fornecedor"}),
    ("/titulares/", {"nome": "Fulano", "cpf_cnpj": "123"}),
    ("/categorias/", {"nome": "ADMIN", "tipo": "despesa"}),
])
def test_ciclo_status(client, url, body):
    # CREATE: status oculto forçado a ATIVO (mesmo se o cliente tentar enviar outro)
    r = client.post(url, json={**body, "status": "INATIVO"})
    assert r.status_code == 201 and r.json()["status"] == "ATIVO"
    id_ = r.json()["id"]
    # UPDATE não altera status
    campo = next(iter(body))
    r = client.put(f"{url}{id_}", json={campo: "NOVO", "status": "INATIVO"})
    assert r.status_code == 200 and r.json()["status"] == "ATIVO" and r.json()[campo] == "NOVO"
    # DELETE lógico
    assert client.delete(f"{url}{id_}").status_code == 200
    assert client.get(f"{url}{id_}").json()["status"] == "INATIVO"  # continua no BD
    assert client.get(url).json() == []                              # TODOS => só ATIVO
    assert len(client.get(url, params={"status": "INATIVO"}).json()) == 1
    # Reativar
    assert client.patch(f"{url}{id_}/reativar").json()["status"] == "ATIVO"
    assert len(client.get(url).json()) == 1


def test_busca_multi_criterio(client):
    client.post("/parceiros/", json={"nome_razao": "Alfa Peças", "cnpj_cpf": "11.111.111/0001-00", "tipo": "FORNECEDOR"})
    client.post("/parceiros/", json={"nome_razao": "Alfa Cliente", "cnpj_cpf": "22222222000100", "tipo": "CLIENTE"})
    r = client.get("/parceiros/", params={"nome": "alfa", "tipo": "FORNECEDOR"}).json()
    assert len(r) == 1 and r[0]["tipo"] == "FORNECEDOR"
    assert len(client.get("/parceiros/", params={"documento": "11111111"}).json()) == 1


def test_verificar_e_lancar(client):
    v = client.post("/documentos/verificar", json=DANFE).json()
    assert not v["fornecedor"]["existe"] and not v["faturado"]["existe"] and not v["despesa"]["existe"]

    r = client.post("/documentos/lancar", json=DANFE)
    assert r.status_code == 200, r.text
    assert set(r.json()["criados"]) == {"fornecedor", "faturado", "despesa"}

    v = client.post("/documentos/verificar", json=DANFE).json()
    assert v["fornecedor"]["existe"] and v["faturado"]["existe"] and v["despesa"]["existe"]

    regs = client.get("/registros/", params={"tipo": "APAGAR"}).json()
    assert len(regs) == 1 and len(regs[0]["parcelas"]) == 2 and regs[0]["status"] == "ATIVO"
    assert regs[0]["parceiro"] == "IGUAÇU MAQUINAS LTDA"

    # segundo lançamento reutiliza cadastros existentes
    r2 = client.post("/documentos/lancar", json=DANFE).json()
    assert r2["criados"] == []


def test_lancar_invalido_faz_rollback(client):
    ruim = {**DANFE, "classificacao_despesa": ""}
    assert client.post("/documentos/lancar", json=ruim).status_code == 422
    assert client.get("/parceiros/").json() == []


def test_registro_crud_logico(client):
    p = client.post("/parceiros/", json={"nome_razao": "X", "cnpj_cpf": "1", "tipo": "CLIENTE"}).json()
    body = {"tipo": "areceber", "valor_total": 100, "data_emissao": "2026-10-01", "parceiro_id": p["id"],
            "parcelas": [{"data_vencimento": "2026-11-01", "valor": 60}, {"data_vencimento": "2026-12-01", "valor": 40}]}
    r = client.post("/registros/", json=body)
    assert r.status_code == 201 and r.json()["tipo"] == "ARECEBER" and r.json()["status"] == "ATIVO"
    id_ = r.json()["id"]
    assert client.put(f"/registros/{id_}", json={**body, "valor_total": 100}).json()["status"] == "ATIVO"
    client.delete(f"/registros/{id_}")
    assert client.get("/registros/").json() == []
    assert client.patch(f"/registros/{id_}/reativar").json()["status"] == "ATIVO"
