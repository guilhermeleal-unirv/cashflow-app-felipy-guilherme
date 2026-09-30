from sqlmodel import Field, SQLModel

class UserBase(SQLModel):
    """Classe base para Usuários. Contém os dados em comum."""
    username: str = Field(index=True, unique=True)
    email: str | None = Field(default=None)
    is_active: bool = Field(default=True)

class User(UserBase, table=True):
    """Modelo que representa a tabela 'user' no banco de dados."""
    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str

class UserCreate(UserBase):
    """Schema utilizado para criar um usuário."""
    password: str

class UserUpdate(SQLModel):
    """Schema utilizado para atualizar um usuário (PUT/PATCH)."""
    username: str | None = None
    email: str | None = None
    password: str | None = None
    is_active: bool | None = None

class UserLogin(SQLModel):
    """Schema simplificado para receber apenas username e password no login (via JSON)."""
    username: str
    password: str

class UserRead(UserBase):
    id: int
