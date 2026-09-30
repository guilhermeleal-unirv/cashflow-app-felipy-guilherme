# CASHFLOW API — Controle de Contas Rurais

Bem-vindo ao projeto **CASHFLOW**. Esta API foi construída com **FastAPI**, utilizando **Pydantic** para validação de dados, **SQLModel** para comunicação com o banco de dados e integração com **PostgreSQL**. O sistema tem como objetivo o controle financeiro de propriedades rurais com extração automática de dados de notas fiscais via **Inteligência Artificial (Google Gemini)**.

---

## 🗂 Estrutura do Projeto

```
📦 FastAPI_BD-main
├── api/
│   ├── auth.py              # Endpoints de autenticação (login, token JWT)
│   ├── users.py             # CRUD de usuários
│   ├── titular.py           # CRUD de titulares (Fulano, Beltrano, Ciclano)
│   ├── parceiro.py          # CRUD de parceiros (Fornecedores/Clientes)
│   ├── categoria.py         # CRUD de categorias de despesa
│   ├── documento.py         # Upload de PDF + Extração via LLM (Gemini)
│   └── registro_financeiro.py  # Registros financeiros e baixas de parcelas
├── models/
│   ├── user.py              # Modelo de usuário e autenticação
│   ├── token.py             # Schemas de token JWT
│   └── financeiro.py        # Modelos: Titular, Parceiro, Categoria,
│                            #  DocumentoPDF, RegistroFinanceiro, Parcela, DepositoBaixa
├── services/                # Lógica de negócio e serviços
├── auth/                    # Geração e verificação de tokens JWT
├── integration/
│   └── database.py          # Conexão e criação das tabelas no banco (lifespan)
├── static/
│   └── index.html           # Interface web para extração de PDF via LLM
├── main.py                  # Entry point — registra todos os routers
├── requirements.txt
└── .env                     # Variáveis de ambiente (DATABASE_URL)
```

---

## 🛠 Pré-requisitos

- **Python 3.10+** instalado na sua máquina.
- **PostgreSQL** instalado e rodando.
- Uma **Chave da API do Google Gemini** (obtida em [aistudio.google.com](https://aistudio.google.com)).
- (Opcional) **Insomnia**, **Postman** ou o **Swagger UI** embutido para testar os endpoints.

---

## 📝 Passo a Passo da Configuração

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
> - **psycopg2-binary** — Driver de conexão com o PostgreSQL.
> - **python-dotenv** — Lê variáveis de ambiente do arquivo `.env`.
> - **PyPDF2** — Extração de texto de arquivos PDF.
> - **google-generativeai** — SDK oficial da API do Google Gemini (LLM).

### Passo 4: Configurar as Variáveis de Ambiente (`.env`)

Abra o arquivo `.env` e ajuste a `DATABASE_URL` com os dados da sua instalação do PostgreSQL:

```env
DATABASE_URL=postgresql://seu_usuario:sua_senha@localhost:5432/cashflow_db
```

### Passo 5: Rodar a Aplicação

Com o ambiente virtual ativado e as dependências instaladas, rode:

```bash
uvicorn main:app --reload
```

- `--reload` faz o servidor reiniciar automaticamente ao salvar qualquer arquivo.
- Na primeira inicialização, **todas as tabelas serão criadas automaticamente** no banco de dados.

---

## 🚀 Funcionalidades Implementadas

### 🔐 Autenticação (JWT)
- `POST /auth/login` — Realiza o login e retorna um token JWT.

### 👤 Usuários
- `POST /users` — Cria um novo usuário.
- `GET /users` — Lista todos os usuários.
- `GET /users/{id}` — Busca um usuário específico.
- `PUT /users/{id}` — Atualiza um usuário.
- `DELETE /users/{id}` — Remove um usuário.

### 🏠 Titulares
Representam os proprietários rurais (Fulano, Beltrano, Ciclano).
- `POST /titulares/` — Cadastra um titular.
- `GET /titulares/` — Lista todos os titulares.
- `GET /titulares/{id}` — Busca um titular.
- `DELETE /titulares/{id}` — Remove um titular.

### 🤝 Parceiros (Fornecedores/Clientes)
- `POST /parceiros/` — Cadastra um parceiro.
- `GET /parceiros/` — Lista todos os parceiros.
- `GET /parceiros/{id}` — Busca um parceiro.
- `DELETE /parceiros/{id}` — Remove um parceiro.

### 🏷️ Categorias de Despesa
- `POST /categorias/` — Cadastra uma categoria.
- `GET /categorias/` — Lista todas as categorias.
- `GET /categorias/{id}` — Busca uma categoria.
- `DELETE /categorias/{id}` — Remove uma categoria.

### 📄 Documentos PDF e Extração via LLM ⭐
- `GET /documentos/` — Lista PDFs cadastrados, com filtro por status (`Pendente`, `Aprovado`, `Erro`).
- `POST /documentos/upload` — Upload manual de um PDF, cria o pré-cadastro com status "Pendente".
- `POST /documentos/{id}/aprovar` — Valida os dados extraídos e cria o Registro Financeiro + Parcela automaticamente.
- `POST /documentos/{id}/reprocessar` — Reenvia o documento para processamento.
- `POST /documentos/extrair_via_llm` — **Endpoint principal da Etapa 1.** Recebe um PDF e uma Gemini API Key, extrai via LLM e retorna o seguinte JSON:

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
  "classificacao_despesa": "MANUTENÇÃO E OPERAÇÃO"
}
```

> O campo `classificacao_despesa` é **interpretado pelo Gemini** com base nos produtos da nota, e não simplesmente extraído. As categorias disponíveis são: INSUMOS AGRÍCOLAS, MANUTENÇÃO E OPERAÇÃO, RECURSOS HUMANOS, SERVIÇOS OPERACIONAIS, INFRAESTRUTURA E UTILIDADES, ADMINISTRATIVAS, SEGUROS E PROTEÇÃO, IMPOSTOS E TAXAS, INVESTIMENTOS.

### 💰 Registros Financeiros e Parcelas
- `GET /registros/` — Lista todos os lançamentos financeiros aprovados.
- `GET /registros/{id}` — Detalha um registro.
- `GET /registros/parcelas/{id}` — Detalha uma parcela.
- `POST /registros/parcelas/{id}/baixa` — Registra um depósito/pagamento parcial. O sistema liquida a parcela automaticamente quando o total depositado atingir o valor da parcela.

---

## 🌐 Interface Web (Frontend)

Após iniciar o servidor, acesse a interface de extração de PDF:

```
http://localhost:8000/static/index.html
```

Na interface você pode:
1. Carregar uma Nota Fiscal em formato PDF.
2. Informar a sua **Gemini API Key**.
3. Clicar em **"Analisar com IA"**.
4. Visualizar todos os dados extraídos organizados na tela (Fornecedor, Faturado, Parcelas, Classificação de Despesa) e o JSON completo.

---

## 📖 Documentação Interativa da API (Swagger)

Com o servidor rodando, acesse:

```
http://localhost:8000/docs
```

Lá você encontra todos os endpoints documentados e pode testá-los diretamente pelo navegador com o botão **"Try it out"**.

---

Desenvolvido por **Guilherme Leal** e **Felipy Chimango** — N2 Engenharia de Software 🎓
