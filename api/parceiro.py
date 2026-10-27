from api.crud_base import make_crud_router
from models.financeiro import Parceiro, ParceiroCreate, ParceiroUpdate, ParceiroRead

parceiro_router = make_crud_router(
    prefix="/parceiros", tag="Parceiros (Fornecedor/Cliente)", rotulo="Parceiro",
    Model=Parceiro, Create=ParceiroCreate, Update=ParceiroUpdate, Read=ParceiroRead,
    text_filters={"nome": "nome_razao"},
    digit_filters={"documento": "cnpj_cpf"},
    exact_filters=("tipo",),
)
