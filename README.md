# CASHFLOW API â€” Controle de Contas Rurais

Bem-vindo ao projeto **CASHFLOW**. Esta API foi construÃ­da com **FastAPI**, utilizando **Pydantic** para validaÃ§Ã£o de dados, **SQLModel** para comunicaÃ§Ã£o com o banco de dados e integraÃ§Ã£o com **PostgreSQL**. O sistema tem como objetivo o controle financeiro de propriedades rurais com extraÃ§Ã£o automÃ¡tica de dados de notas fiscais via **InteligÃªncia Artificial (Google Gemini)**.

---

## ðŸ—‚ Estrutura do Projeto

```
ðŸ“¦ FastAPI_BD-main
â”œâ”€â”€ api/
â”‚   â”œâ”€â”€ auth.py              # Endpoints de autenticaÃ§Ã£o (login, token JWT)
â”‚   â”œâ”€â”€ users.py             # CRUD de usuÃ¡rios
â”‚   â”œâ”€â”€ titular.py           # CRUD de titulares (Fulano, Beltrano, Ciclano)
â”‚   â”œâ”€â”€ parceiro.py          # CRUD de parceiros (Fornecedores/Clientes)
â”‚   â”œâ”€â”€ categoria.py         # CRUD de categorias de despesa
â”‚   â”œâ”€â”€ documento.py         # Upload de PDF + ExtraÃ§Ã£o via LLM (Gemini)
â”‚   â””â”€â”€ registro_financeiro.py  # Registros financeiros e baixas de parcelas
â”œâ”€â”€ models/
â”‚   â”œâ”€â”€ user.py              # Modelo de usuÃ¡rio e autenticaÃ§Ã£o
â”‚   â”œâ”€â”€ token.py             # Schemas de token JWT
â”‚   â””â”€â”€ financeiro.py        # Modelos: Titular, Parceiro, Categoria,
â”‚                            #  DocumentoPDF, RegistroFinanceiro, Parcela, DepositoBaixa
â”œâ”€â”€ services/                # LÃ³gica de negÃ³cio e serviÃ§os
â”œâ”€â”€ auth/                    # GeraÃ§Ã£o e verificaÃ§Ã£o de tokens JWT
â”œâ”€â”€ integration/
â”‚   â””â”€â”€ database.py          # ConexÃ£o e criaÃ§Ã£o das tabelas no banco (lifespan)
â”œâ”€â”€ static/
â”‚   â””â”€â”€ index.html           # Interface web para extraÃ§Ã£o de PDF via LLM
â”œâ”€â”€ main.py                  # Entry point â€” registra todos os routers
â”œâ”€â”€ requirements.txt
â””â”€â”€ .env                     # VariÃ¡veis de ambiente (DATABASE_URL)
```

---

## ðŸ›  PrÃ©-requisitos

- **Python 3.10+** instalado na sua mÃ¡quina.
- **PostgreSQL** instalado e rodando.
- Uma **Chave da API do Google Gemini** (obtida em [aistudio.google.com](https://aistudio.google.com)).
- (Opcional) **Insomnia**, **Postman** ou o **Swagger UI** embutido para testar os endpoints.

---

## ðŸ“� Passo a Passo da ConfiguraÃ§Ã£o

### Passo 1: Preparar o Banco de Dados (PostgreSQL)
1. Abra o seu servidor do PostgreSQL (via DBeaver, pgAdmin ou terminal).
2. Crie um banco de dados novo. SugestÃ£o de nome: `cashflow_db`.
3. Anote o **usuÃ¡rio**, **senha**, **host** e **porta** da sua conexÃ£o.

> **AtenÃ§Ã£o:** O FastAPI cria as tabelas automaticamente na inicializaÃ§Ã£o. VocÃª nÃ£o precisa criar nenhuma tabela manualmente.

### Passo 2: Criar e Ativar um Ambiente Virtual

**No Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**No Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Passo 3: Instalar as DependÃªncias

```bash
pip install -r requirements.txt
```

> **O que estÃ¡ sendo instalado:**
> - **fastapi** â€” Framework web de alta performance.
> - **uvicorn[standard]** â€” Servidor ASGI para rodar a aplicaÃ§Ã£o.
> - **sqlmodel** â€” IntegraÃ§Ã£o moderna de Pydantic + SQLAlchemy para o banco de dados.
> - **psycopg2-binary** â€” Driver de conexÃ£o com o PostgreSQL.
> - **python-dotenv** â€” LÃª variÃ¡veis de ambiente do arquivo `.env`.
> - **PyPDF2** â€” ExtraÃ§Ã£o de texto de arquivos PDF.
> - **google-generativeai** â€” SDK oficial da API do Google Gemini (LLM).

### Passo 4: Configurar as VariÃ¡veis de Ambiente (`.env`)

Abra o arquivo `.env` e ajuste a `DATABASE_URL` com os dados da sua instalaÃ§Ã£o do PostgreSQL:

```env
DATABASE_URL=postgresql://seu_usuario:sua_senha@localhost:5432/cashflow_db
```

### Passo 5: Rodar a AplicaÃ§Ã£o

Com o ambiente virtual ativado e as dependÃªncias instaladas, rode:

```bash
uvicorn main:app --reload
```

- `--reload` faz o servidor reiniciar automaticamente ao salvar qualquer arquivo.
- Na primeira inicializaÃ§Ã£o, **todas as tabelas serÃ£o criadas automaticamente** no banco de dados.

---

## ðŸš€ Funcionalidades Implementadas

### ðŸ”� AutenticaÃ§Ã£o (JWT)
- `POST /auth/login` â€” Realiza o login e retorna um token JWT.

### ðŸ‘¤ UsuÃ¡rios
- `POST /users` â€” Cria um novo usuÃ¡rio.
- `GET /users` â€” Lista todos os usuÃ¡rios.
- `GET /users/{id}` â€” Busca um usuÃ¡rio especÃ­fico.
- `PUT /users/{id}` â€” Atualiza um usuÃ¡rio.
- `DELETE /users/{id}` â€” Remove um usuÃ¡rio.

### ðŸ�  Titulares
Representam os proprietÃ¡rios rurais (Fulano, Beltrano, Ciclano).
- `POST /titulares/` â€” Cadastra um titular.
- `GET /titulares/` â€” Lista todos os titulares.
- `GET /titulares/{id}` â€” Busca um titular.
- `DELETE /titulares/{id}` â€” Remove um titular.

### ðŸ¤� Parceiros (Fornecedores/Clientes)
- `POST /parceiros/` â€” Cadastra um parceiro.
- `GET /parceiros/` â€” Lista todos os parceiros.
- `GET /parceiros/{id}` â€” Busca um parceiro.
- `DELETE /parceiros/{id}` â€” Remove um parceiro.

### ðŸ�·ï¸� Categorias de Despesa
- `POST /categorias/` â€” Cadastra uma categoria.
- `GET /categorias/` â€” Lista todas as categorias.
- `GET /categorias/{id}` â€” Busca uma categoria.
- `DELETE /categorias/{id}` â€” Remove uma categoria.

### ðŸ“„ Documentos PDF e ExtraÃ§Ã£o via LLM â­�
- `GET /documentos/` â€” Lista PDFs cadastrados, com filtro por status (`Pendente`, `Aprovado`, `Erro`).
- `POST /documentos/upload` â€” Upload manual de um PDF, cria o prÃ©-cadastro com status "Pendente".
- `POST /documentos/{id}/aprovar` â€” Valida os dados extraÃ­dos e cria o Registro Financeiro + Parcela automaticamente.
- `POST /documentos/{id}/reprocessar` â€” Reenvia o documento para processamento.
- `POST /documentos/extrair_via_llm` â€” **Endpoint principal da Etapa 1.** Recebe um PDF e uma Gemini API Key, extrai via LLM e retorna o seguinte JSON:

```json
{
  "fornecedor": {
    "razao_social": "...",
    "fantasia": "...",
    "cnpj": "..."
  },
  "faturado": {
    "nome_completo": "...",
    "cpf": "..."
  },
  "numero_nota_fiscal": "...",
  "data_emissao": "YYYY-MM-DD",
  "descricao_produtos": "...",
  "parcelas": [
    { "numero": 1, "data_vencimento": "YYYY-MM-DD", "valor": 0.00 }
  ],
  "valor_total": 0.00,
  "classificacao_despesa": "MANUTENÃ‡ÃƒO E OPERAÃ‡ÃƒO"
}
```

> O campo `classificacao_despesa` Ã© **interpretado pelo Gemini** com base nos produtos da nota, e nÃ£o simplesmente extraÃ­do. As categorias disponÃ­veis sÃ£o: INSUMOS AGRÃ�COLAS, MANUTENÃ‡ÃƒO E OPERAÃ‡ÃƒO, RECURSOS HUMANOS, SERVIÃ‡OS OPERACIONAIS, INFRAESTRUTURA E UTILIDADES, ADMINISTRATIVAS, SEGUROS E PROTEÃ‡ÃƒO, IMPOSTOS E TAXAS, INVESTIMENTOS.

### ðŸ’° Registros Financeiros e Parcelas
- `GET /registros/` â€” Lista todos os lanÃ§amentos financeiros aprovados.
- `GET /registros/{id}` â€” Detalha um registro.
- `GET /registros/parcelas/{id}` â€” Detalha uma parcela.
- `POST /registros/parcelas/{id}/baixa` â€” Registra um depÃ³sito/pagamento parcial. O sistema liquida a parcela automaticamente quando o total depositado atingir o valor da parcela.

---

## ðŸŒ� Interface Web (Frontend)

ApÃ³s iniciar o servidor, acesse a interface de extraÃ§Ã£o de PDF:

```
http://localhost:8000/static/index.html
```

Na interface vocÃª pode:
1. Carregar uma Nota Fiscal em formato PDF.
2. Informar a sua **Gemini API Key**.
3. Clicar em **"Analisar com IA"**.
4. Visualizar todos os dados extraÃ­dos organizados na tela (Fornecedor, Faturado, Parcelas, ClassificaÃ§Ã£o de Despesa) e o JSON completo.

---

## ðŸ“– DocumentaÃ§Ã£o Interativa da API (Swagger)

Com o servidor rodando, acesse:

```
http://localhost:8000/docs
```

LÃ¡ vocÃª encontra todos os endpoints documentados e pode testÃ¡-los diretamente pelo navegador com o botÃ£o **"Try it out"**.

---

Desenvolvido por **Guilherme Leal** e **Felipy Chimango** â€” N2 Engenharia de Software ðŸŽ“

## N2 - Etapa 2
- Tela inicial: `/` (SPA em `static/`). Lançar via IA: extrai o DANFE, consulta Fornecedor/Faturado/Despesa (EXISTE/NÃO EXISTE), cria o que faltar e lança o movimento A PAGAR com parcelas (`POST /documentos/verificar` e `/documentos/lancar`).
- CRUDs com exclusão lógica (STATUS ATIVO/INATIVO, reativação): `/parceiros`, `/titulares`, `/categorias`, `/registros`.
- Migração automática das colunas novas no startup (`integration/migrations.py`).
- Testes: `python -m pytest -q tests`.
- Deploy: `render.yaml` (Render Blueprint, Postgres incluso).

---

## 🚀 N3 - 3ª Etapa: Consulta com Agente Inteligente (RAG)
**Entrega: 02/12/2026 | Peso: 60% Entrega + 40% Avaliação**

Implementação completa do padrão **Retrieval-Augmented Generation (RAG)** integrado ao CASHFLOW:

### 1. 🔹 RAG Simples (Peso: 25%)
- **Retriever:** Consulta SQLModel no banco relacional buscando registros financeiros ativos, parceiros, titulares e parcelas.
- **Augmentation:** Montagem de prompt estruturado alimentado com o contexto tabular recuperado.
- **Generator:** Modelo Gemini (`gemini-2.0-flash` / `gemini-1.5-flash`) gera respostas sintetizadas e fundamentadas no banco.

### 2. 🔸 RAG Embeddings / Semântico (Peso: 35%)
- **Indexação Vetorial:** Vetorização dos registros financeiros e notas fiscais com modelo de embeddings (`models/text-embedding-004`).
- **Retriever Semântico:** Cálculo de proximidade conceitual via **Similaridade de Cosseno** entre o embedding da pergunta e os documentos indexados.
- **Geração:** Injeção dos documentos semanticamente mais relevantes no prompt do Gemini, permitindo encontrar dados mesmo sem correspondência literal de palavras (ex: *"peças e manutenção"* recupera itens agrícolas).

### 3. 🖥️ Interface Web do Agente RAG
- Acessível na barra lateral: **🤖 Consulta RAG (N3)**.
- Input para perguntas em linguagem natural + botões de exemplos rápidos.
- Seletor de método: **RAG Simples**, **RAG Embeddings** ou **Comparar Ambos (Lado a Lado)**.
- **Transparência RAG:** Exibição do retorno elaborado pelo LLM e lista das fontes e registros recuperados do banco (com score de similaridade).

### 4. 🔌 Endpoints da API (`/rag`)
- `POST /rag/consultar`: Executa a busca e geração com o Agente RAG.
- `GET /rag/status`: Estatísticas de registros ativos e cache vetorial.
- `POST /rag/reindexar`: Atualização e pré-aquecimento dos embeddings.
