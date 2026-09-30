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
          "emitente": {{
            "razao_social": "Razão Social da empresa emitente (campo RAZÃO SOCIAL / NOME no cabeçalho do DANFE)",
            "fantasia": "Nome Fantasia do emitente (campo NOME FANTASIA abaixo da razão social). Se esse campo não existir na nota, retorne null",
            "cnpj": "apenas os 14 dígitos numéricos do CNPJ do EMITENTE que aparece no cabeçalho após o rótulo C.N.P.J. — nunca use o CNPJ do destinatário aqui",
            "ie": "Inscrição Estadual do emitente, apenas números, ou null",
            "endereco": "Logradouro e número do emitente",
            "municipio": "Município do emitente",
            "uf": "UF do emitente, 2 letras",
            "cep": "CEP apenas números, ou null",
            "fone": "Telefone do emitente, ou null"
          }},
          "destinatario": {{
            "nome_razao": "Nome completo ou Razão Social do destinatário",
            "cnpj_cpf": "apenas os dígitos numéricos do CNPJ ou CPF do destinatário (seção DESTINATÁRIO)",
            "ie": "Inscrição Estadual do destinatário, ou null",
            "endereco": "Endereço completo do destinatário",
            "municipio": "Município do destinatário",
            "uf": "UF do destinatário, 2 letras"
          }},
          "nota_fiscal": {{
            "numero": "número da NF-e",
            "serie": "série da NF-e",
            "data_emissao": "YYYY-MM-DD",
            "natureza_operacao": "natureza da operação descrita no cabeçalho da NF",
            "tipo_operacao": "0 para Entrada ou 1 para Saída"
          }},
          "totais": {{
            "valor_total_produtos": 0.00,
            "bc_icms": 0.00,
            "valor_icms": 0.00,
            "bc_icms_st": 0.00,
            "valor_icms_st": 0.00,
            "valor_ipi": 0.00,
            "valor_pis": 0.00,
            "valor_cofins": 0.00,
            "valor_frete": 0.00,
            "valor_seguro": 0.00,
            "desconto": 0.00,
            "outras_despesas": 0.00,
            "valor_total_nota": 0.00
          }},
          "itens": [
            {{
              "codigo": "código do produto, ou null",
              "descricao": "descrição completa do produto/serviço",
              "ncm": "código NCM sem pontos ou traços",
              "cst": "código CST, ou null",
              "cfop": "código CFOP, ou null",
              "unidade": "unidade de medida (UN, PC, KG, L, etc.)",
              "quantidade": 0,
              "valor_unitario": 0.00,
              "valor_total": 0.00,
              "bc_icms": 0.00,
              "valor_icms": 0.00,
              "valor_ipi": 0.00,
              "aliquota_icms": 0.00,
              "aliquota_ipi": 0.00
            }}
          ],
          "transportador": {{
            "razao_social": "Razão Social do transportador, ou null",
            "cnpj_cpf": "apenas dígitos do CNPJ/CPF do transportador, ou null",
            "frete_por_conta": "código: 0=Emitente, 1=Destinatário, 9=Sem Frete",
            "placa_veiculo": "placa do veículo, ou null",
            "uf_veiculo": "UF do veículo, ou null"
          }},
          "parcelas": [
            {{
              "numero": 1,
              "data_vencimento": "YYYY-MM-DD",
              "valor": 0.00
            }}
          ],
          "classificacao_despesa": "categoria interpretada pelos produtos (veja categorias abaixo)"
        }}

        REGRAS CRÍTICAS DE EXTRAÇÃO:
        - NOME FANTASIA: procure o campo literalmente chamado NOME FANTASIA no cabeçalho. Se não existir esse campo explícito, coloque null — não invente.
        - CNPJ do emitente: use SOMENTE o número após o rótulo "C.N.P.J." na seção do EMITENTE (cabeçalho). Remova pontos, barras e traços. Resultado: 14 dígitos.
        - CNPJ/CPF do destinatário: use SOMENTE o número após "C.N.P.J." ou "C.P.F." na seção DESTINATÁRIO/COMPRADOR. São diferentes do emitente.
        - ITENS: extraia TODOS os itens da tabela DADOS DOS PRODUTOS/SERVIÇOS, um objeto por linha.
        - TOTAIS: preencha com os valores da seção de totais/cálculo do imposto. Use 0.00 se não encontrar (nunca null para valores numéricos).
        - classificacao_despesa: interprete os produtos e escolha UMA categoria:
          INSUMOS AGRÍCOLAS | MANUTENÇÃO E OPERAÇÃO | RECURSOS HUMANOS | SERVIÇOS OPERACIONAIS |
          INFRAESTRUTURA E UTILIDADES | ADMINISTRATIVAS | SEGUROS E PROTEÇÃO | IMPOSTOS E TAXAS | INVESTIMENTOS
        - Todos os valores monetários devem ser números com ponto decimal (ex: 1045.39). Nunca strings.
        - Se não encontrar data de vencimento nas parcelas/duplicatas, use a data de emissão.
        - Use null para campos de texto não encontrados.

        Texto do PDF:
        {texto}
        """
        response = model.generate_content(prompt)
        
        # Parseia a resposta do LLM (remove markdown caso presente)
        texto_resposta = response.text.strip()
        texto_resposta = re.sub(r'^```json\s*', '', texto_resposta)
        texto_resposta = re.sub(r'```\s*$', '', texto_resposta)
        
        json_match = re.search(r'\{.*\}', texto_resposta, re.DOTALL)
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
