# CASHFLOW API — Controle de Contas Rurais

Bem-vindo ao projeto **CASHFLOW**. Esta API foi construída com **FastAPI**, utilizando **Pydantic** para validação de dados, **SQLModel** para comunicação com o banco de dados e integração com **PostgreSQL**. O sistema tem como objetivo o controle financeiro de propriedades rurais com extração automática de dados de notas fiscais via **Inteligência Artificial (Google Gemini)** e consultas inteligentes via **RAG (Retrieval-Augmented Generation)**.

---

## 🗂️ Estrutura do Projeto

```
📦 FastAPI_BD-main
├── api/
│   ├── auth.py                # Endpoints de autenticação (login, token JWT)
│   ├── users.py               # CRUD de usuários
│   ├── titular.py             # CRUD de titulares (Fulano, Beltrano, Ciclano)
│   ├── parceiro.py            # CRUD de parceiros (Fornecedores/Clientes)
│   ├── categoria.py           # CRUD de categorias de despesa
│   ├── documento.py           # Upload de PDF + Extração via LLM (Gemini)
│   ├── registro_financeiro.py # Registros financeiros e baixas de parcelas
│   └── rag.py                 # Endpoints de Consulta RAG (Simples e Embeddings)
├── models/
│   ├── user.py                # Modelo de usuário e autenticação
│   ├── token.py               # Schemas de token JWT
│   └── financeiro.py          # Modelos: Titular, Parceiro, Categoria, DocumentoPDF,
│                              # RegistroFinanceiro, Parcela, DepositoBaixa
├── services/
│   ├── agent_rag.py           # Agente Inteligente RAG (Simples + Embeddings)
│   ├── lancamento_service.py  # Lógica de verificação e lançamento automático
│   ├── auth_service.py        # Autenticação e hash de senhas
│   └── user_service.py        # Serviços de usuário
├── auth/                      # Geração e verificação de tokens JWT
├── integration/
│   ├── database.py            # Conexão e criação das tabelas no banco (lifespan)
│   └── migrations.py          # Migrações automáticas de schema
├── static/
│   ├── index.html             # Interface web SPA (Lançar via IA, CRUDs, Consulta RAG)
│   ├── css/app.css            # Estilos da aplicação
│   └── js/                    # Scripts da interface (app.js, crud.js)
├── tests/                     # Testes automatizados (pytest)
│   ├── test_etapa2.py         # Testes de autenticação, CRUDs e lançamento
│   └── test_rag.py            # Testes do motor RAG (Simples e Embeddings)
├── main.py                    # Entry point — registra todos os routers
├── requirements.txt
└── .env                       # Variáveis de ambiente (DATABASE_URL, SECRET_KEY)
```

---

## 🛠️ Pré-requisitos

- **Python 3.10+** instalado na sua máquina.
- **PostgreSQL** instalado e rodando (ou SQLite para testes locais).
- Uma **Chave da API do Google Gemini** (obtida em [aistudio.google.com](https://aistudio.google.com)).
- (Opcional) **Insomnia**, **Postman** ou o **Swagger UI** embutido para testar os endpoints.

---

## 📋 Passo a Passo da Configuração

### Passo 1: Preparar o Banco de Dados (PostgreSQL)
1. Abra o seu servidor do PostgreSQL (via DBeaver, pgAdmin ou terminal).
2. Crie um banco de dados novo. Sugestão de nome: `cashflow_db`.
3. Anote o **usuário**, **senha**, **host** e **porta** da sua conexão.

> **Atenção:** O FastAPI cria as tabelas automaticamente na inicialização. Você não precisa criar nenhuma tabela manualmente.

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

### Passo 3: Instalar as Dependências

```bash
pip install -r requirements.txt
```

> **O que está sendo instalado:**
> - **fastapi** — Framework web de alta performance.
> - **uvicorn[standard]** — Servidor ASGI para rodar a aplicação.
> - **sqlmodel** — Integração moderna de Pydantic + SQLAlchemy para o banco de dados.
> - **psycopg2-binary** / **psycopg** — Drivers de conexão com o PostgreSQL.
> - **python-dotenv** — Lê variáveis de ambiente do arquivo `.env`.
> - **PyPDF2** — Extração de texto de arquivos PDF.
> - **google-generativeai** — SDK oficial da API do Google Gemini (LLM e Embeddings).
> - **python-jose[cryptography]** / **bcrypt** — Autenticação e segurança JWT.

### Passo 4: Configurar as Variáveis de Ambiente (`.env`)

Crie ou ajuste o arquivo `.env`:

```env
DATABASE_URL=postgresql://seu_usuario:sua_senha@localhost:5432/cashflow_db
SECRET_KEY="sua_chave_secreta_jwt"
GEMINI_API_KEY="sua_chave_gemini_opcional"
```

### Passo 5: Rodar a Aplicação

Com o ambiente virtual ativado e as dependências instaladas, rode:

```bash
uvicorn main:app --reload
```

- `--reload` faz o servidor reiniciar automaticamente ao salvar qualquer arquivo.
- Na primeira inicialização, **todas as tabelas serão criadas automaticamente** e o usuário padrão `joao.paraiba` será populado no banco de dados.

---

## 🚀 Funcionalidades Implementadas

### 🔒 Autenticação (JWT)
- `POST /login` — Realiza o login e retorna um token JWT Bearer.
- Usuário padrão seedado: `joao.paraiba` / Senha: `costelaoNoDomingo`.

### 👤 Usuários
- `POST /users` — Cria um novo usuário.
- `GET /users` — Lista todos os usuários.
- `GET /users/{id}` — Busca um usuário específico.
- `PUT /users/{id}` — Atualiza um usuário.
- `DELETE /users/{id}` — Remove um usuário.

### 🏡 Titulares (Faturados)
Representam os proprietários rurais (Fulano, Beltrano, Ciclano).
- `POST /titulares/` — Cadastra um titular.
- `GET /titulares/` — Lista todos os titulares (com busca multi-critério).
- `GET /titulares/{id}` — Busca um titular.
- `DELETE /titulares/{id}` — Inativa um titular (exclusão lógica).

### 🤝 Parceiros (Fornecedores/Clientes)
- `POST /parceiros/` — Cadastra um parceiro.
- `GET /parceiros/` — Lista todos os parceiros.
- `GET /parceiros/{id}` — Busca um parceiro.
- `DELETE /parceiros/{id}` — Inativa um parceiro (exclusão lógica).

### 🏷️ Categorias de Despesa / Receita
- `POST /categorias/` — Cadastra uma categoria.
- `GET /categorias/` — Lista todas as categorias.
- `GET /categorias/{id}` — Busca uma categoria.
- `DELETE /categorias/{id}` — Inativa uma categoria (exclusão lógica).

### 📄 Documentos PDF e Extração via LLM (N1 / N2)
- `POST /documentos/extrair_via_llm` — Extrai dados completos do DANFE/NF-e via Gemini.
- `POST /documentos/verificar` — Verifica no banco se fornecedor, faturado e classificação já existem ou estão inativos.
- `POST /documentos/lancar` — Cria entidades ausentes, reativa inativos e gera o movimento A PAGAR com suas parcelas automaticamente.

### 💰 Registros Financeiros e Parcelas
- `GET /registros/` — Lista todos os lançamentos financeiros com filtros e paginação.
- `POST /registros/` — Criação manual de contas a pagar/receber com parcelamento.
- `POST /registros/parcelas/{id}/baixa` — Registra depósito ou liquidação de parcelas.

---

## 🤖 N3 - Consulta com Agente Inteligente (RAG)
**Entrega: 02/12/2026 | Peso: 60% Entrega + 40% Avaliação**

Implementação completa da arquitetura **RAG (Retrieval-Augmented Generation)**:

### 1. 🔹 RAG Simples (Peso: 25%)
- **Retriever:** Consulta estruturada SQLModel no banco relacional buscando registros financeiros ativos, fornecedores, faturados, categorias e parcelas.
- **Augmentation:** Montagem de prompt estruturado alimentado com o contexto tabular recuperado.
- **Generator:** Modelo Gemini (`gemini-2.0-flash` / `gemini-1.5-flash`) sintetiza respostas precisas e fundamentadas nos dados reais.

### 2. 🔸 RAG Embeddings / Semântico (Peso: 35%)
- **Indexação Vetorial:** Vetorização dos registros com modelo de embeddings (`models/text-embedding-004`).
- **Retriever Semântico:** Busca conceitual por proximidade vetorial calculando a **Similaridade de Cosseno** contra o vetor da pergunta do usuário.
- **Geração:** Injeção dos trechos semanticamente mais relevantes no prompt do Gemini, permitindo encontrar dados mesmo sem correspondência literal de palavras (ex: *"peças e manutenção"* recupera registros agrícolas relevantes).

### 3. 🖥️ Interface Web do Agente RAG
- Acessível na barra lateral: **🤖 Consulta RAG (N3)**.
- Input para perguntas em linguagem natural + botões de exemplos rápidos.
- Seletor de método: **RAG Simples**, **RAG Embeddings** ou **Comparar Ambos (Lado a Lado)**.
- **Transparência RAG:** Exibição da resposta elaborada pelo LLM e lista das fontes e registros recuperados do banco (com score de similaridade).

### 4. 🔌 Endpoints da API (`/rag`)
- `POST /rag/consultar` — Executa a busca e geração com o Agente RAG.
- `GET /rag/status` — Estatísticas de registros ativos e cache vetorial.
- `POST /rag/reindexar` — Atualização e pré-aquecimento dos embeddings.

---

## 🌐 Interface Web (Frontend)

Após iniciar o servidor, acesse a interface web completa:

```
http://localhost:8000/static/index.html
```

Na interface você pode:
1. Fazer login com o usuário padrão (`joao.paraiba` / `costelaoNoDomingo`).
2. Lançar Notas Fiscais via IA (upload de PDF + conferência + persistência).
3. Gerenciar todos os cadastros e movimentações financeiras.
4. Consultar o banco via **Agente RAG** nos modos **Simples** e **Embeddings**.

---

## 📖 Documentação Interativa da API (Swagger)

Com o servidor rodando, acesse:

```
http://localhost:8000/docs
```

Lá você encontra todos os endpoints documentados e pode testá-los diretamente pelo navegador com o botão **"Try it out"**.

---

Desenvolvido por **Guilherme Leal** e **Felipy Chimango** — Engenharia de Software (UniRV) 🎓
