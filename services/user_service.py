from sqlmodel import select
from integration.database import SessionDep
from models import User, UserCreate, UserUpdate
from auth.security import get_password_hash

def create_user(session: SessionDep, user: UserCreate) -> User | None:
    statement = select(User).where(User.username == user.username)
    if session.exec(statement).first():
        return None
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password),
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

def get_users(session: SessionDep, skip: int = 0, limit: int = 100) -> list[User]:
    return session.exec(select(User).offset(skip).limit(limit)).all()

def get_user(session: SessionDep, user_id: int) -> User | None:
    return session.get(User, user_id)

def update_user(session: SessionDep, user_id: int, user_update: UserUpdate) -> User | None:
    db_user = session.get(User, user_id)
    if not db_user:
        return None
    user_data = user_update.model_dump(exclude_unset=True)
    if "password" in user_data:
        db_user.hashed_password = get_password_hash(user_data["password"])
        del user_data["password"]
    for key, value in user_data.items():
        setattr(db_user, key, value)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

def delete_user(session: SessionDep, user_id: int) -> bool:
    db_user = session.get(User, user_id)
    if not db_user:
        return False
    session.delete(db_user)
    session.commit()
    return True
