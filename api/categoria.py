from api.crud_base import make_crud_router
from models.financeiro import Categoria, CategoriaCreate, CategoriaUpdate, CategoriaRead

categoria_router = make_crud_router(
    prefix="/categorias", tag="Categorias (Classificação)", rotulo="Classificação",
    Model=Categoria, Create=CategoriaCreate, Update=CategoriaUpdate, Read=CategoriaRead,
    text_filters={"nome": "nome"},
    exact_filters=("tipo",),
)
