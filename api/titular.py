from api.crud_base import make_crud_router
from models.financeiro import Titular, TitularCreate, TitularUpdate, TitularRead

titular_router = make_crud_router(
    prefix="/titulares", tag="Titulares (Faturado)", rotulo="Faturado",
    Model=Titular, Create=TitularCreate, Update=TitularUpdate, Read=TitularRead,
    text_filters={"nome": "nome"},
    digit_filters={"documento": "cpf_cnpj"},
)
