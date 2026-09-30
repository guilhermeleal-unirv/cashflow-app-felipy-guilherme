from fastapi import APIRouter, Depends, HTTPException, status
from integration.database import SessionDep
from models import Token, UserCreate, UserLogin, UserRead
from services import auth_service

auth_router = APIRouter(tags=["Autenticação"])

@auth_router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, session: SessionDep):
    db_user = auth_service.register_user(session, user)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username já registrado",
        )
    return db_user

@auth_router.post("/login", response_model=Token)
def login_for_access_token(session: SessionDep, user_login: UserLogin):
    access_token = auth_service.authenticate_user(session, user_login)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": access_token, "token_type": "bearer"}
