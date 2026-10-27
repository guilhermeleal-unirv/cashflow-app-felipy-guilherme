from typing import Optional, List
from datetime import date, datetime, timezone
from sqlmodel import SQLModel, Field, Relationship

# Valores permitidos para o campo STATUS (exclusão lógica)
STATUS_ATIVO = "ATIVO"
STATUS_INATIVO = "INATIVO"

# ==========================================
# Titular (PESSOAS - Tipo FATURADO)
# ==========================================
class TitularBase(SQLModel):
    nome: str = Field(index=True)
    cpf_cnpj: str = Field(index=True)

class Titular(TitularBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    status: str = Field(default=STATUS_ATIVO, index=True)
    registros: List["RegistroFinanceiro"] = Relationship(back_populates="titular")

class TitularCreate(TitularBase):
    pass  # STATUS oculto: o servidor força ATIVO

class TitularUpdate(SQLModel):
    nome: Optional[str] = None
    cpf_cnpj: Optional[str] = None

class TitularRead(TitularBase):
    id: int
    status: str


# ==========================================
# Parceiro (PESSOAS - Tipo CLIENTE / FORNECEDOR)
# ==========================================
class ParceiroBase(SQLModel):
    nome_razao: str = Field(index=True)
    cnpj_cpf: str = Field(index=True)
    tipo: str  # FORNECEDOR ou CLIENTE

class Parceiro(ParceiroBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    status: str = Field(default=STATUS_ATIVO, index=True)
    registros: List["RegistroFinanceiro"] = Relationship(back_populates="parceiro")

class ParceiroCreate(ParceiroBase):
    pass

class ParceiroUpdate(SQLModel):
    nome_razao: Optional[str] = None
    cnpj_cpf: Optional[str] = None
    tipo: Optional[str] = None

class ParceiroRead(ParceiroBase):
    id: int
    status: str


# ==========================================
# Categoria (CLASSIFICACAO - Tipo DESPESA / RECEITA)
# ==========================================
class CategoriaBase(SQLModel):
    nome: str = Field(index=True)  # descrição da classificação
    tipo: str  # DESPESA ou RECEITA

class Categoria(CategoriaBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    status: str = Field(default=STATUS_ATIVO, index=True)
    registros: List["RegistroFinanceiro"] = Relationship(back_populates="categoria")

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaUpdate(SQLModel):
    nome: Optional[str] = None
    tipo: Optional[str] = None

class CategoriaRead(CategoriaBase):
    id: int
    status: str


# ==========================================
# DocumentoPDF
# ==========================================
class DocumentoPDFBase(SQLModel):
    nome_arquivo: str
    status_ocr: str  # Ex: Pendente, Aprovado, Erro
    data_importacao: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DocumentoPDF(DocumentoPDFBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    registros: List["RegistroFinanceiro"] = Relationship(back_populates="documento_pdf")

class DocumentoPDFCreate(DocumentoPDFBase):
    pass

class DocumentoPDFRead(DocumentoPDFBase):
    id: int


# ==========================================
# RegistroFinanceiro (MOVIMENTOCONTAS)
# ==========================================
class RegistroFinanceiroBase(SQLModel):
    valor_total: float
    data_emissao: date
    tipo: str = Field(default="APAGAR", index=True)  # APAGAR ou ARECEBER
    titular_id: Optional[int] = Field(default=None, foreign_key="titular.id")
    parceiro_id: Optional[int] = Field(default=None, foreign_key="parceiro.id")
    categoria_id: Optional[int] = Field(default=None, foreign_key="categoria.id")
    pdf_id: Optional[int] = Field(default=None, foreign_key="documentopdf.id")

class RegistroFinanceiro(RegistroFinanceiroBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    status: str = Field(default=STATUS_ATIVO, index=True)

    titular: Optional[Titular] = Relationship(back_populates="registros")
    parceiro: Optional[Parceiro] = Relationship(back_populates="registros")
    categoria: Optional[Categoria] = Relationship(back_populates="registros")
    documento_pdf: Optional[DocumentoPDF] = Relationship(back_populates="registros")

    parcelas: List["Parcela"] = Relationship(back_populates="registro_financeiro")

class RegistroFinanceiroCreate(RegistroFinanceiroBase):
    pass

class RegistroFinanceiroRead(RegistroFinanceiroBase):
    id: int
    status: str


# ==========================================
# RegistroCategoria (um movimento pode ter 1..N classificações)
# ==========================================
class RegistroCategoria(SQLModel, table=True):
    registro_id: int = Field(foreign_key="registrofinanceiro.id", primary_key=True)
    categoria_id: int = Field(foreign_key="categoria.id", primary_key=True)


# ==========================================
# Parcela (PARCELACONTAS)
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
