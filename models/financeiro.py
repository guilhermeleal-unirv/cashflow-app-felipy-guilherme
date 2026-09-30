from typing import Optional, List
from datetime import date, datetime
from sqlmodel import SQLModel, Field, Relationship

# ==========================================
# Titular
# ==========================================
class TitularBase(SQLModel):
    nome: str
    cpf_cnpj: str

class Titular(TitularBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    registros: List["RegistroFinanceiro"] = Relationship(back_populates="titular")

class TitularCreate(TitularBase):
    pass

class TitularRead(TitularBase):
    id: int


# ==========================================
# Parceiro
# ==========================================
class ParceiroBase(SQLModel):
    nome_razao: str
    cnpj_cpf: str
    tipo: str  # Ex: Fornecedor, Cliente

class Parceiro(ParceiroBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    registros: List["RegistroFinanceiro"] = Relationship(back_populates="parceiro")

class ParceiroCreate(ParceiroBase):
    pass

class ParceiroRead(ParceiroBase):
    id: int


# ==========================================
# Categoria
# ==========================================
class CategoriaBase(SQLModel):
    nome: str
    tipo: str  # Ex: Insumos, Operacional, Venda (Receita)

class Categoria(CategoriaBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    registros: List["RegistroFinanceiro"] = Relationship(back_populates="categoria")

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaRead(CategoriaBase):
    id: int


# ==========================================
# DocumentoPDF
# ==========================================
class DocumentoPDFBase(SQLModel):
    nome_arquivo: str
    status_ocr: str  # Ex: Pendente, Aprovado, Erro
    data_importacao: datetime = Field(default_factory=datetime.utcnow)

class DocumentoPDF(DocumentoPDFBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    registros: List["RegistroFinanceiro"] = Relationship(back_populates="documento_pdf")

class DocumentoPDFCreate(DocumentoPDFBase):
    pass

class DocumentoPDFRead(DocumentoPDFBase):
    id: int


# ==========================================
# RegistroFinanceiro
# ==========================================
class RegistroFinanceiroBase(SQLModel):
    valor_total: float
    data_emissao: date
    titular_id: Optional[int] = Field(default=None, foreign_key="titular.id")
    parceiro_id: Optional[int] = Field(default=None, foreign_key="parceiro.id")
    categoria_id: Optional[int] = Field(default=None, foreign_key="categoria.id")
    pdf_id: Optional[int] = Field(default=None, foreign_key="documentopdf.id")

class RegistroFinanceiro(RegistroFinanceiroBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    titular: Optional[Titular] = Relationship(back_populates="registros")
    parceiro: Optional[Parceiro] = Relationship(back_populates="registros")
    categoria: Optional[Categoria] = Relationship(back_populates="registros")
    documento_pdf: Optional[DocumentoPDF] = Relationship(back_populates="registros")
    
    parcelas: List["Parcela"] = Relationship(back_populates="registro_financeiro")

class RegistroFinanceiroCreate(RegistroFinanceiroBase):
    pass

class RegistroFinanceiroRead(RegistroFinanceiroBase):
    id: int


# ==========================================
# Parcela
# ==========================================
class ParcelaBase(SQLModel):
    numero_parcela: int
    data_vencimento: date
    valor_parcela: float
    status: str  # Ex: Pendente, Liquidada
    registro_id: int = Field(foreign_key="registrofinanceiro.id")

class Parcela(ParcelaBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    registro_financeiro: RegistroFinanceiro = Relationship(back_populates="parcelas")
    depositos: List["DepositoBaixa"] = Relationship(back_populates="parcela")

class ParcelaCreate(ParcelaBase):
    pass

class ParcelaRead(ParcelaBase):
    id: int


# ==========================================
# DepositoBaixa
# ==========================================
class DepositoBaixaBase(SQLModel):
    data_deposito: date
    valor_depositado: float
    comprovante: Optional[str] = None
    parcela_id: int = Field(foreign_key="parcela.id")

class DepositoBaixa(DepositoBaixaBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    parcela: Parcela = Relationship(back_populates="depositos")

class DepositoBaixaCreate(DepositoBaixaBase):
    pass

class DepositoBaixaRead(DepositoBaixaBase):
    id: int
