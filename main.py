"""
Arquivo principal (entry point) da aplicação FastAPI.
Aqui nós configuramos a instância principal do app, middlewares (como CORS) 
e incluímos as rotas (routers) definidas em outros arquivos.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import auth_router
from api.users import users_router
from api.titular import titular_router
from api.parceiro import parceiro_router
from api.categoria import categoria_router
from api.documento import documento_router
from api.registro_financeiro import registro_router
from integration.database import lifespan

from fastapi.staticfiles import StaticFiles

# Criação da instância principal da aplicação FastAPI
# O parâmetro 'lifespan' permite executar código antes da API começar a receber requisições (ex: criar tabelas).
app = FastAPI(
    title="CodeGuild API",
    description="Backend da aplicação CodeGuild.",
    version="1.0.0",
    lifespan=lifespan
)

# ==========================================
# Configuração do Middleware de CORS (Cross-Origin Resource Sharing)
# ==========================================
# O CORS é um mecanismo de segurança dos navegadores que impede que um site de uma origem 
# (ex: http://meu-frontend.com) acesse recursos de outra origem (ex: http://minha-api.com).
# Para permitir que o frontend (ex: React rodando na porta 3000) consuma esta API (rodando na porta 8000),
# precisamos configurar explicitamente essas políticas.
#
# AVISO PARA PRODUÇÃO: O uso de `allow_origins=["*"]` permite que QUALQUER site faça requisições
# para a sua API. Em um ambiente real, você deve listar apenas os domínios confiáveis.
# Exemplo seguro: allow_origins=["http://localhost:3000", "https://meu-site-oficial.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em ambiente de aula deixamos aberto ("*"), mas com o alerta acima!
    allow_credentials=True, # Permite envio de cookies e cabeçalhos de autenticação (como o Bearer JWT)
    allow_methods=["*"],  # Permite todos os métodos HTTP (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Permite todos os cabeçalhos (essencial para receber o "Authorization: Bearer <token>")
)

# Registramos as rotas de autenticação (login e registro)
app.include_router(auth_router)

# Inclui as rotas (endpoints) de CRUD de usuários
app.include_router(users_router)

# Rotas do sistema CASHFLOW
app.include_router(titular_router)
app.include_router(parceiro_router)
app.include_router(categoria_router)
app.include_router(documento_router)
app.include_router(registro_router)

# Frontend para o Leitor de LLM
import os
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
