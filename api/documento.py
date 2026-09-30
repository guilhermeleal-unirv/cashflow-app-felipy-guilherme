from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from typing import Optional, List
from datetime import date
from pydantic import BaseModel
from sqlmodel import select
from integration.database import SessionDep
import io
import PyPDF2
import google.generativeai as genai
import json
import re
from models.financeiro import DocumentoPDF, DocumentoPDFRead, RegistroFinanceiro, Parcela

documento_router = APIRouter(prefix="/documentos", tags=["Documentos"])

class AprovarPDFPayload(BaseModel):
    titular_id: int
    parceiro_id: int
    categoria_id: int
    valor_total: float
    data_vencimento: date

@documento_router.get("/", response_model=list[DocumentoPDFRead])
def listar_documentos(
    session: SessionDep,
    status_ocr: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    query = select(DocumentoPDF)
    if status_ocr:
        query = query.where(DocumentoPDF.status_ocr == status_ocr)
    documentos = session.exec(query.offset(skip).limit(limit)).all()
    return documentos

@documento_router.post("/upload", response_model=DocumentoPDFRead, status_code=status.HTTP_201_CREATED)
def upload_manual(
    session: SessionDep,
    file: UploadFile = File(...)
):
    # Simula o recebimento do arquivo e a pré-leitura via OCR
    # Na prática, salvaríamos o 'file' no disco ou cloud
    
    novo_doc = DocumentoPDF(
        nome_arquivo=file.filename,
        status_ocr="Pendente"
    )
    session.add(novo_doc)
    session.commit()
    session.refresh(novo_doc)
    
    return novo_doc

@documento_router.post("/{doc_id}/reprocessar")
def reprocessar_ocr(doc_id: int, session: SessionDep):
    doc = session.get(DocumentoPDF, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    
    # Aqui chamaria o serviço de OCR verdadeiro (Motor Parser PDF)
    # Por enquanto, só simulamos que o status voltou para pendente ou sucesso
    doc.status_ocr = "Pendente"
    session.add(doc)
    session.commit()
    
    return {"message": "Reprocessamento de OCR simulado com sucesso.", "status": doc.status_ocr}

@documento_router.post("/{doc_id}/aprovar")
def aprovar_documento(
    doc_id: int,
    payload: AprovarPDFPayload,
    session: SessionDep
):
    # 1. Buscar o PDF e validar
    doc = session.get(DocumentoPDF, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    if doc.status_ocr == "Aprovado":
        raise HTTPException(status_code=400, detail="Este documento já foi aprovado")

    # 2. Criar o Registro Financeiro
    novo_registro = RegistroFinanceiro(
        valor_total=payload.valor_total,
        data_emissao=date.today(), # ou buscar do payload
        titular_id=payload.titular_id,
        parceiro_id=payload.parceiro_id,
        categoria_id=payload.categoria_id,
        pdf_id=doc.id
    )
    session.add(novo_registro)
    session.commit()
    session.refresh(novo_registro)
    
    # 3. Gerar a 1ª Parcela vinculada ao registro
    nova_parcela = Parcela(
        numero_parcela=1,
        data_vencimento=payload.data_vencimento,
        valor_parcela=payload.valor_total,
        status="Pendente",
        registro_id=novo_registro.id
    )
    session.add(nova_parcela)
    
    # 4. Atualizar o status do Documento
    doc.status_ocr = "Aprovado"
    session.add(doc)
    
    session.commit()
    return {"message": "Documento aprovado e Registro Financeiro criado com sucesso!", "registro_id": novo_registro.id}

@documento_router.post("/extrair_via_llm")
def extrair_via_llm(
    file: UploadFile = File(...),
    api_key: str = Form(...)
):
    try:
        # Lê o conteúdo do PDF
        pdf_content = file.file.read()
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
        texto = ""
        for page in pdf_reader.pages:
            texto_extraido = page.extract_text()
            if texto_extraido:
                texto += texto_extraido
            
        # Configura a API do Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-3.8-flash')
        
        prompt = f"""
        Você é um assistente financeiro especialista em notas fiscais brasileiras (DANFE/NF-e).
        Analise o texto abaixo extraído de um PDF e retorne APENAS um objeto JSON válido, sem qualquer texto ou markdown ao redor.
        Siga exatamente esta estrutura:

        {{
          "fornecedor": {{
            "razao_social": "Nome completo da empresa emitente",
            "fantasia": "Nome fantasia, ou null se não houver",
            "cnpj": "apenas números"
          }},
          "faturado": {{
            "nome_completo": "Nome do destinatário/comprador",
            "cpf": "apenas números, ou null se for pessoa jurídica"
          }},
          "numero_nota_fiscal": "número da NF",
          "data_emissao": "YYYY-MM-DD",
          "descricao_produtos": "descrição resumida de todos os produtos/itens da nota",
          "parcelas": [
            {{
              "numero": 1,
              "data_vencimento": "YYYY-MM-DD",
              "valor": 0.00
            }}
          ],
          "valor_total": 0.00,
          "classificacao_despesa": "Uma das categorias abaixo, interpretada pelos produtos da nota"
        }}

        REGRAS IMPORTANTES:
        - O campo "classificacao_despesa" NÃO deve ser extraído diretamente da nota. Você deve INTERPRETAR os produtos e escolher a categoria mais adequada:
        - INSUMOS AGRÍCOLAS: Sementes, Fertilizantes, Defensivos, Corretivos
        - MANUTENÇÃO E OPERAÇÃO: Combustíveis, Peças, Parafusos, Componentes Mecânicos, Pneus, Filtros, Ferramentas
        - RECURSOS HUMANOS: Mão de Obra, Salários
        - SERVIÇOS OPERACIONAIS: Frete, Transporte, Colheita, Secagem, Armazenagem
        - INFRAESTRUTURA E UTILIDADES: Energia Elétrica, Arrendamento, Construções, Materiais de Construção
        - ADMINISTRATIVAS: Honorários, Despesas Bancárias
        - SEGUROS E PROTEÇÃO: Seguro Agrícola, Seguro de Ativos
        - IMPOSTOS E TAXAS: ITR, IPTU, IPVA
        - INVESTIMENTOS: Aquisição de Máquinas, Veículos, Imóveis
        - Se houver apenas uma parcela, coloque o array com um elemento. O valor da parcela deve ser igual ao valor total.
        - Se não encontrar a data de vencimento, use a data de emissão.
        - Use null para campos não encontrados.

        Texto do PDF:
        {texto}
        """
        response = model.generate_content(prompt)
        
        # Parseia a resposta do LLM (remove markdown caso presente)
        texto_resposta = response.text.strip()
        texto_resposta = re.sub(r'^```json\s*', '', texto_resposta)
        texto_resposta = re.sub(r'```\s*$', '', texto_resposta)
        
        json_match = re.search(r'\{{.*\}}', texto_resposta, re.DOTALL)
        if json_match:
            dados = json.loads(json_match.group())
            return dados
        else:
            # Tenta parsear direto
            try:
                dados = json.loads(texto_resposta)
                return dados
            except:
                raise HTTPException(status_code=500, detail=f"O modelo não retornou JSON válido. Resposta: {texto_resposta[:300]}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao extrair dados via LLM: {str(e)}")
