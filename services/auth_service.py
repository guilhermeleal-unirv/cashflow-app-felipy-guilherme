from sqlmodel import select
from integration.database import SessionDep
from models import User, UserCreate, UserLogin
from auth.security import get_password_hash, verify_password, create_access_token

def register_user(session: SessionDep, user_data: UserCreate) -> User | None:
    statement = select(User).where(User.username == user_data.username)
    if session.exec(statement).first():
        return None
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

def authenticate_user(session: SessionDep, user_login: UserLogin) -> str | None:
    statement = select(User).where(User.username == user_login.username)
    user = session.exec(statement).first()
    if not user or not verify_password(user_login.password, user.hashed_password):
        return None
    return create_access_token(data={"sub": user.username})
