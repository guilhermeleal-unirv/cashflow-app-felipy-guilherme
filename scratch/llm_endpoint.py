import io
import PyPDF2
import google.generativeai as genai
import json
import re

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
            if page.extract_text():
                texto += page.extract_text()
            
        # Configura a API do Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Você é um assistente financeiro especialista em notas fiscais e comprovantes.
        Analise o texto abaixo que foi extraído de um PDF e retorne APENAS um objeto JSON (sem formatação markdown) com as seguintes chaves:
        {{
            "cnpj_cpf_emitente": "apenas numeros",
            "valor_total": float (use ponto para decimais),
            "data_vencimento": "YYYY-MM-DD"
        }}
        Se não encontrar o vencimento, use a data de emissão. Se não achar nenhuma data, coloque a data de hoje.
        
        Texto do PDF:
        {texto}
        """
        response = model.generate_content(prompt)
        
        # Parseia a resposta do LLM
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            dados = json.loads(json_match.group())
            return dados
        else:
            raise HTTPException(status_code=500, detail="O modelo não retornou um formato JSON válido.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao extrair dados via LLM: {str(e)}")
