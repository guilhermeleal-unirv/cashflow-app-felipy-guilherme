"""
Módulo do Agente Inteligente RAG (Retrieval-Augmented Generation) para o CASHFLOW.
Implementa as duas abordagens exigidas na N3:
1. RAG Simples: Recuperação estruturada direta do Banco de Dados + Aumento de Prompt + Geração LLM.
2. RAG Embeddings / Semântico: Vetorização semântica de notas/registros + Busca por similaridade de cosseno + Aumento + Geração LLM.
"""

import os
import math
import re
import unicodedata
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Tuple

import google.generativeai as genai
from sqlmodel import Session, select

from models.financeiro import (
    RegistroFinanceiro, Parcela, Parceiro, Titular, Categoria,
    RegistroCategoria, DocumentoPDF, STATUS_ATIVO,
)

# Cache em memória para embeddings de registros para otimizar chamadas à API
_EMBEDDINGS_CACHE: Dict[str, List[float]] = {}


def _normalizar_texto(texto: str) -> str:
    s = unicodedata.normalize("NFD", str(texto or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip().lower()


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Calcula a similaridade de cosseno entre dois vetores."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def _termo_vetor_fallback(texto: str, vocabulario: List[str]) -> List[float]:
    """Fallback local para vetorização semântica por termos (em caso de limite de cota de API)."""
    tokens = set(_normalizar_texto(texto).split())
    return [1.0 if t in tokens else 0.0 for t in vocabulario]


class AgentRAG:
    """
    Agente RAG responsável pelo ciclo completo:
    1. Retrieval (Recuperação de dados estruturados ou por Embeddings)
    2. Augmentation (Injeção de contexto no prompt)
    3. Generation (Geração de resposta fundamentada com Google Gemini)
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("LLM_KEY")
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
            except Exception as e:
                print(f"[AgentRAG] Aviso ao configurar API Key: {e}")

        # Modelos padrão sugeridos nos slides da disciplina
        self.model_name = "gemini-2.0-flash"
        self.embedding_model = "models/text-embedding-004"

    def _obter_modelo_gerativo(self, api_key: Optional[str] = None):
        chave = api_key or self.api_key
        if chave:
            genai.configure(api_key=chave)

        candidatos = [
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest",
            "gemini-pro",
        ]
        ultimo_erro = None
        for nome in candidatos:
            try:
                modelo = genai.GenerativeModel(nome)
                return modelo
            except Exception as e:
                ultimo_erro = e
                continue
        raise RuntimeError(f"Não foi possível instanciar nenhum modelo Gemini. Erro: {ultimo_erro}")

    def _carregar_registros_completos(self, session: Session, limite: int = 50) -> List[Dict[str, Any]]:
        """Recupera todos os registros ativos com relacionamentos completos carregados."""
        query = select(RegistroFinanceiro).where(RegistroFinanceiro.status == STATUS_ATIVO).order_by(RegistroFinanceiro.id.desc()).limit(limite)
        registros_db = session.exec(query).all()

        documentos = []
        for r in registros_db:
            p = session.get(Parceiro, r.parceiro_id) if r.parceiro_id else None
            t = session.get(Titular, r.titular_id) if r.titular_id else None

            # Categorias associadas
            cat_ids = [rc.categoria_id for rc in session.exec(
                select(RegistroCategoria).where(RegistroCategoria.registro_id == r.id)).all()]
            if r.categoria_id and r.categoria_id not in cat_ids:
                cat_ids.insert(0, r.categoria_id)
            categorias = [session.get(Categoria, cid) for cid in cat_ids]
            categorias_str = ", ".join(c.nome for c in categorias if c) or "Não informada"

            # Parcelas
            parcelas = session.exec(
                select(Parcela).where(Parcela.registro_id == r.id).order_by(Parcela.numero_parcela)
            ).all()

            pdf = session.get(DocumentoPDF, r.pdf_id) if r.pdf_id else None

            parcelas_info = [
                {
                    "numero": p_item.numero_parcela,
                    "vencimento": p_item.data_vencimento.isoformat() if p_item.data_vencimento else None,
                    "valor": float(p_item.valor_parcela),
                    "status": p_item.status
                }
                for p_item in parcelas
            ]

            doc_dict = {
                "id": r.id,
                "tipo": r.tipo,
                "valor_total": float(r.valor_total),
                "data_emissao": r.data_emissao.isoformat() if r.data_emissao else None,
                "parceiro": p.nome_razao if p else "Não informado",
                "parceiro_doc": p.cnpj_cpf if p else None,
                "parceiro_tipo": p.tipo if p else None,
                "titular": t.nome if t else "Não informado",
                "titular_doc": t.cpf_cnpj if t else None,
                "categoria": categorias_str,
                "documento_pdf": pdf.nome_arquivo if pdf else None,
                "status": r.status,
                "parcelas": parcelas_info,
            }

            # Monta texto semântico descritivo para vetorização e recuperação
            doc_dict["texto_semantico"] = (
                f"Registro Financeiro #{doc_dict['id']} ({doc_dict['tipo']}): "
                f"Valor Total: R$ {doc_dict['valor_total']:.2f}. "
                f"Data de Emissão: {doc_dict['data_emissao']}. "
                f"Fornecedor/Cliente (Parceiro): {doc_dict['parceiro']} (Doc: {doc_dict['parceiro_doc'] or 'N/A'}, Tipo: {doc_dict['parceiro_tipo'] or 'N/A'}). "
                f"Faturado para (Titular): {doc_dict['titular']} (CPF/CNPJ: {doc_dict['titular_doc'] or 'N/A'}). "
                f"Classificação/Categoria: {doc_dict['categoria']}. "
                f"Arquivo PDF de Origem: {doc_dict['documento_pdf'] or 'Nenhum'}. "
                f"Parcelas: " + "; ".join(
                    [f"Parcela {p['numero']}: R$ {p['valor']:.2f} com vencimento em {p['vencimento']} ({p['status']})" for p in parcelas_info]
                )
            )

            documentos.append(doc_dict)

        return documentos

    # =========================================================
    # 1. RAG SIMPLES (Recuperação direta tabular do Banco)
    # =========================================================
    def _retrieve_data_simple(self, session: Session, query: str, limite: int = 25) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Retriever Simples: Consulta direta aos registros ativos do banco de dados
        (equivalente ao _retrieve_data dos slides de aula).
        """
        documentos = self._carregar_registros_completos(session, limite=limite)

        linhas_texto = []
        for d in documentos:
            linhas_texto.append(
                f"- [ID {d['id']}] Tipo: {d['tipo']} | Valor: R$ {d['valor_total']:.2f} | "
                f"Emissão: {d['data_emissao']} | Fornecedor/Cliente: {d['parceiro']} | "
                f"Faturado: {d['titular']} | Classificação: {d['categoria']} | "
                f"Parcelas: {len(d['parcelas'])} | PDF: {d['documento_pdf'] or 'N/A'}"
            )

        contexto_estruturado = "\n".join(linhas_texto) if linhas_texto else "Nenhum registro financeiro encontrado no banco de dados."
        return contexto_estruturado, documentos

    # =========================================================
    # 2. RAG EMBEDDINGS (Recuperação Vetorial por Similaridade)
    # =========================================================
    def _gerar_embedding(self, texto: str, api_key: Optional[str] = None) -> List[float]:
        """Gera embedding do texto via Gemini API com fallback inteligente."""
        chave = api_key or self.api_key
        if chave:
            try:
                genai.configure(api_key=chave)
                result = genai.embed_content(
                    model=self.embedding_model,
                    content=texto,
                    task_type="retrieval_document"
                )
                if result and "embedding" in result:
                    return result["embedding"]
            except Exception as e:
                print(f"[AgentRAG] Aviso embedding Gemini: {e}")

        # Fallback local se não houver chave ou exceder quota
        tokens_base = [
            "nota", "fiscal", "manutencao", "operacao", "insumos", "agricolas", "trator",
            "pecas", "peca", "maquinas", "combustivel", "adubo", "pagar", "receber",
            "vencimento", "parcela", "fornecedor", "cliente", "faturado", "titular",
            "valor", "total", "iguaçu", "beltrano", "ciclano", "fulano", "agro"
        ]
        return _termo_vetor_fallback(texto, tokens_base)

    def _retrieve_data_embeddings(
        self,
        session: Session,
        query: str,
        top_k: int = 5,
        api_key: Optional[str] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Retriever Semântico com Embeddings:
        1. Vetoriza os registros (armazenamento e indexação de embeddings).
        2. Vetoriza a pergunta do usuário.
        3. Calcula a similaridade de cosseno.
        4. Retorna os top_k registros semanticamente mais relevantes.
        """
        documentos = self._carregar_registros_completos(session, limite=100)
        if not documentos:
            return "Nenhum registro financeiro encontrado no banco de dados.", []

        # 1. Vetoriza pergunta do usuário
        query_embedding = self._gerar_embedding(query, api_key=api_key)

        # 2. Vetoriza cada documento com cache
        ranqueados = []
        for doc in documentos:
            cache_key = f"doc_{doc['id']}_{doc['valor_total']}_{doc['categoria']}"
            if cache_key in _EMBEDDINGS_CACHE:
                doc_vec = _EMBEDDINGS_CACHE[cache_key]
            else:
                doc_vec = self._gerar_embedding(doc["texto_semantico"], api_key=api_key)
                _EMBEDDINGS_CACHE[cache_key] = doc_vec

            score = _cosine_similarity(query_embedding, doc_vec)
            doc_copia = dict(doc)
            doc_copia["similaridade_score"] = round(score, 4)
            ranqueados.append((score, doc_copia))

        # 3. Ordena pela maior proximidade semântica
        ranqueados.sort(key=lambda x: x[0], reverse=True)
        selecionados = [item[1] for item in ranqueados[:top_k]]

        linhas_contexto = []
        for i, doc in enumerate(selecionados, 1):
            linhas_contexto.append(
                f"[Documento Relevante #{i} - Similaridade: {doc.get('similaridade_score', 0):.2%}]\n"
                f"{doc['texto_semantico']}\n"
            )

        contexto = "\n".join(linhas_contexto)
        return contexto, selecionados

    # =========================================================
    # 3. GENERATION (Geração de resposta fundamentada)
    # =========================================================
    def _generate_response(
        self,
        user_query: str,
        retrieved_data: str,
        modo: str,
        api_key: Optional[str] = None
    ) -> str:
        """
        Etapa de Aumento (Augmentation) e Geração (Generation):
        Monta o prompt enriquecido com os dados do banco e chama o LLM Gemini.
        """
        prompt = f"""
Você é um assistente inteligente de gestão financeira e auditoria do sistema rural CASHFLOW.
Sua missão é responder à pergunta do usuário utilizando ESTRITAMENTE as informações dos registros recuperados do banco de dados.

DIRETRIZES FUNDAMENTAIS:
1. Baseie-se APENAS nos dados fornecidos na seção "DADOS RECUPERADOS DO BANCO". Nunca invente ou deduza informações que não estejam presentes.
2. Se a informação não puder ser respondida com base nos dados recuperados, afirme educadamente que não constam registros no banco para essa consulta.
3. Apresente valores monetários sempre no padrão brasileiro (ex: R$ 1.250,00) e datas no formato DD/MM/AAAA.
4. Identifique o fornecedor, faturado, valores, parcelas ou categorias sempre que relevante para a pergunta.
5. No final da resposta, inclua uma breve observação técnica informando que os dados foram recuperados via: {modo.upper()}.

DADOS RECUPERADOS DO BANCO:
{retrieved_data}

PERGUNTA DO USUÁRIO:
{user_query}

RESPOSTA CLARA E OBJETIVA:
"""
        chave = api_key or self.api_key
        if not chave:
            return (
                "⚠️ **Aviso:** Nenhuma chave da API do Google Gemini (API Key) foi configurada. "
                "Para gerar respostas com o LLM, informe sua chave no campo apropriado ou defina no arquivo .env.\n\n"
                f"**Dados recuperados pelo Retriever ({modo.upper()}):**\n\n{retrieved_data}"
            )

        try:
            modelo = self._obter_modelo_gerativo(api_key=chave)
            response = modelo.generate_content(prompt)
            if response and getattr(response, "text", None):
                return response.text.strip()
            return "O modelo de IA não retornou texto na resposta."
        except Exception as e:
            return (
                f"⚠️ Ocorreu um erro ao comunicar com a API do Google Gemini: {str(e)}.\n\n"
                f"**Dados recuperados pelo Retriever ({modo.upper()}):**\n\n{retrieved_data}"
            )

    # =========================================================
    # MÉTODO PÚBLICO PRINCIPAL
    # =========================================================
    def consultar(
        self,
        session: Session,
        query: str,
        modo: str = "simples",
        top_k: int = 5,
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executa a consulta com RAG no modo solicitado ('simples', 'embeddings' ou 'ambos').
        """
        query_limpa = (query or "").strip()
        if not query_limpa:
            raise ValueError("A pergunta não pode estar vazia.")

        modo_normalizado = modo.lower()

        if modo_normalizado == "ambos":
            # Executa RAG Simples
            ctx_simples, fontes_simples = self._retrieve_data_simple(session, query_limpa)
            resp_simples = self._generate_response(query_limpa, ctx_simples, "RAG Simples (SQL)", api_key=api_key)

            # Executa RAG Embeddings
            ctx_semantico, fontes_semanticas = self._retrieve_data_embeddings(session, query_limpa, top_k=top_k, api_key=api_key)
            resp_semantico = self._generate_response(query_limpa, ctx_semantico, "RAG Embeddings (Semântico)", api_key=api_key)

            return {
                "query": query_limpa,
                "modo": "ambos",
                "simples": {
                    "resposta": resp_simples,
                    "contexto_recuperado": ctx_simples,
                    "fontes": fontes_simples[:10],
                    "total_fontes": len(fontes_simples)
                },
                "embeddings": {
                    "resposta": resp_semantico,
                    "contexto_recuperado": ctx_semantico,
                    "fontes": fontes_semanticas,
                    "total_fontes": len(fontes_semanticas)
                }
            }

        elif modo_normalizado in ("embeddings", "semantico"):
            contexto, fontes = self._retrieve_data_embeddings(session, query_limpa, top_k=top_k, api_key=api_key)
            resposta = self._generate_response(query_limpa, contexto, "RAG Embeddings (Semântico)", api_key=api_key)
            return {
                "query": query_limpa,
                "modo": "embeddings",
                "resposta": resposta,
                "contexto_recuperado": contexto,
                "fontes": fontes,
                "total_fontes": len(fontes)
            }

        else:
            # Modo padrão: Simples
            contexto, fontes = self._retrieve_data_simple(session, query_limpa)
            resposta = self._generate_response(query_limpa, contexto, "RAG Simples (SQL)", api_key=api_key)
            return {
                "query": query_limpa,
                "modo": "simples",
                "resposta": resposta,
                "contexto_recuperado": contexto,
                "fontes": fontes[:15],
                "total_fontes": len(fontes)
            }


# Alias didático compatível com o nome do slide do professor
Agent3 = AgentRAG
