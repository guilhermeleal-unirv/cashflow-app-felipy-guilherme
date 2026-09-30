from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlmodel import select

from integration.database import SessionDep
from models import User, TokenData
from auth.security import SECRET_KEY, ALGORITHM

security_bearer = HTTPBearer()

def get_current_user(
    session: SessionDep,
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),  # noqa: B008
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = session.exec(select(User).where(User.username == token_data.username)).first()
    if user is None:
        raise credentials_exception

    return user
