"""
Serviço da Etapa 2: verifica no BD se Fornecedor / Faturado / Despesa existem
e realiza o lançamento (criando o que faltar + movimento + parcelas).
"""
import re
import unicodedata
from datetime import date, datetime
from sqlmodel import Session, select

from models.financeiro import (
    Parceiro, Titular, Categoria, RegistroFinanceiro, RegistroCategoria,
    Parcela, DocumentoPDF, STATUS_ATIVO, STATUS_INATIVO,
)


def digitos(v) -> str:
    return re.sub(r"\D", "", str(v or ""))


def normalizar(v) -> str:
    s = unicodedata.normalize("NFD", str(v or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip().lower()


def _fmt_cnpj_cpf(d: str) -> str:
    if len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    return d


def _achar_parceiro(session: Session, cnpj: str):
    if not cnpj:
        return None
    for p in session.exec(select(Parceiro).where(Parceiro.tipo == "FORNECEDOR")).all():
        if digitos(p.cnpj_cpf) == cnpj:
            return p
    return None


def _achar_titular(session: Session, doc: str):
    if not doc:
        return None
    for t in session.exec(select(Titular)).all():
        if digitos(t.cpf_cnpj) == doc:
            return t
    return None


def _achar_categoria(session: Session, nome: str):
    alvo = normalizar(nome)
    if not alvo:
        return None
    for c in session.exec(select(Categoria).where(Categoria.tipo == "DESPESA")).all():
        if normalizar(c.nome) == alvo:
            return c
    return None


def _item(obj, **extra):
    base = {"existe": obj is not None, "id": obj.id if obj else None,
            "inativo": bool(obj and obj.status == STATUS_INATIVO)}
    base.update(extra)
    return base


def _dados_extraidos(dados: dict):
    em = dados.get("emitente") or {}
    dest = dados.get("destinatario") or {}
    return (
        {"razao_social": (em.get("razao_social") or "").strip(), "cnpj": digitos(em.get("cnpj"))},
        {"nome": (dest.get("nome_razao") or "").strip(), "documento": digitos(dest.get("cnpj_cpf"))},
        (dados.get("classificacao_despesa") or "").strip(),
    )


def verificar(session: Session, dados: dict) -> dict:
    forn, fat, desp = _dados_extraidos(dados)
    p = _achar_parceiro(session, forn["cnpj"])
    t = _achar_titular(session, fat["documento"])
    c = _achar_categoria(session, desp)
    return {
        "fornecedor": _item(p, razao_social=forn["razao_social"], cnpj=_fmt_cnpj_cpf(forn["cnpj"])),
        "faturado": _item(t, nome=fat["nome"], documento=_fmt_cnpj_cpf(fat["documento"])),
        "despesa": _item(c, descricao=desp),
    }


def _parse_data(v, padrao: date) -> date:
    if isinstance(v, date):
        return v
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except Exception:
        return padrao


def lancar(session: Session, dados: dict, nome_arquivo: str | None = None) -> dict:
    """Executa em uma única transação; qualquer erro faz rollback."""
    forn, fat, desp = _dados_extraidos(dados)
    if not forn["cnpj"] or not forn["razao_social"]:
        raise ValueError("Fornecedor sem CNPJ/Razão Social no documento extraído")
    if not fat["documento"] or not fat["nome"]:
        raise ValueError("Faturado sem CPF/CNPJ/Nome no documento extraído")
    if not desp:
        raise ValueError("Documento sem classificação de despesa")

    criados = []
    try:
        # 1. Fornecedor
        parceiro = _achar_parceiro(session, forn["cnpj"])
        if not parceiro:
            parceiro = Parceiro(nome_razao=forn["razao_social"], cnpj_cpf=forn["cnpj"],
                                tipo="FORNECEDOR", status=STATUS_ATIVO)
            session.add(parceiro); session.flush(); criados.append("fornecedor")
        elif parceiro.status == STATUS_INATIVO:
            parceiro.status = STATUS_ATIVO; session.add(parceiro)

        # 2. Faturado
        titular = _achar_titular(session, fat["documento"])
        if not titular:
            titular = Titular(nome=fat["nome"], cpf_cnpj=fat["documento"], status=STATUS_ATIVO)
            session.add(titular); session.flush(); criados.append("faturado")
        elif titular.status == STATUS_INATIVO:
            titular.status = STATUS_ATIVO; session.add(titular)

        # 3. Despesa (classificação)
        categoria = _achar_categoria(session, desp)
        if not categoria:
            categoria = Categoria(nome=desp, tipo="DESPESA", status=STATUS_ATIVO)
            session.add(categoria); session.flush(); criados.append("despesa")
        elif categoria.status == STATUS_INATIVO:
            categoria.status = STATUS_ATIVO; session.add(categoria)

        # Documento PDF de origem
        doc = DocumentoPDF(nome_arquivo=nome_arquivo or "extracao_llm.pdf", status_ocr="Aprovado")
        session.add(doc); session.flush()

        nf = dados.get("nota_fiscal") or {}
        totais = dados.get("totais") or {}
        emissao = _parse_data(nf.get("data_emissao"), date.today())
        parcelas_in = dados.get("parcelas") or []
        valor_total = float(totais.get("valor_total_nota") or 0) or \
            sum(float(p.get("valor") or 0) for p in parcelas_in)
        if valor_total <= 0:
            raise ValueError("Valor total da nota não identificado")

        # 4. Movimento (A PAGAR) + parcelas
        registro = RegistroFinanceiro(
            tipo="APAGAR", valor_total=valor_total, data_emissao=emissao,
            titular_id=titular.id, parceiro_id=parceiro.id, categoria_id=categoria.id,
            pdf_id=doc.id, status=STATUS_ATIVO)
        session.add(registro); session.flush()
        session.add(RegistroCategoria(registro_id=registro.id, categoria_id=categoria.id))

        if not parcelas_in:
            parcelas_in = [{"numero": 1, "data_vencimento": emissao.isoformat(), "valor": valor_total}]
        for i, p in enumerate(parcelas_in, start=1):
            session.add(Parcela(
                numero_parcela=int(p.get("numero") or i),
                data_vencimento=_parse_data(p.get("data_vencimento"), emissao),
                valor_parcela=float(p.get("valor") or 0),
                status="Pendente", registro_id=registro.id))
        session.commit()
    except Exception:
        session.rollback()
        raise

    return {
        "message": "Registro lançado com sucesso!",
        "criados": criados,
        "ids": {"fornecedor": parceiro.id, "faturado": titular.id,
                "despesa": categoria.id, "registro": registro.id},
    }
