from sqlmodel import select
from integration.database import SessionDep
from models import Lead, LeadCreate

def create_lead(session: SessionDep, lead: LeadCreate) -> Lead | None:
    statement = select(Lead).where(Lead.email == lead.email)
    if session.exec(statement).first():
        return None
    db_lead = Lead.model_validate(lead)
    session.add(db_lead)
    session.commit()
    session.refresh(db_lead)
    return db_lead

def get_leads(session: SessionDep, skip: int = 0, limit: int = 100) -> list[Lead]:
    return session.exec(select(Lead).offset(skip).limit(limit)).all()
