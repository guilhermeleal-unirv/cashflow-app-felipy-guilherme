from sqlmodel import select
from integration.database import SessionDep
from models import Item, ItemCreate, ItemUpdate

def create_item(session: SessionDep, item: ItemCreate) -> Item:
    db_item = Item.model_validate(item)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item

def get_items(session: SessionDep, skip: int = 0, limit: int = 100) -> list[Item]:
    return session.exec(select(Item).offset(skip).limit(limit)).all()

def get_item(session: SessionDep, item_id: int) -> Item | None:
    return session.get(Item, item_id)

def update_item(session: SessionDep, item_id: int, item_update: ItemUpdate) -> Item | None:
    db_item = session.get(Item, item_id)
    if not db_item:
        return None
    item_data = item_update.model_dump(exclude_unset=True)
    for key, value in item_data.items():
        setattr(db_item, key, value)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item

def delete_item(session: SessionDep, item_id: int) -> bool:
    db_item = session.get(Item, item_id)
    if not db_item:
        return False
    session.delete(db_item)
    session.commit()
    return True
