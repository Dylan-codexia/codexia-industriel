from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from core.config import settings

# Paramètre spécifique à SQLite (pas nécessaire avec PostgreSQL)
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Fournit une session de base de données pour chaque requête.
    La session est fermée automatiquement après la requête.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
