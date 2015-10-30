from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
MemoryBase = declarative_base()
metadata = Base.metadata

# Load our primary database engine
db_engine = create_engine("mysql+pymysql://ene:secret@localhost/ene")
db_session_factory = sessionmaker(bind=db_engine)
Base.metadata.bind = db_engine

# Load our in-memory database engine for session storage
mem_engine = create_engine("sqlite:///:memory:", connect_args={'check_same_thread': False}, poolclass=StaticPool)
mem_session_factory = sessionmaker(bind=mem_engine)
MemoryBase.metadata.bind = mem_engine
MemoryBase.metadata.create_all(mem_engine)


# noinspection PyPep8Naming
def DbSession():
    """
    Create and return a new database session
    """
    return scoped_session(db_session_factory)


# noinspection PyPep8Naming
def MemorySession():
    """
    Create and return a new in-memory SQLite database session
    """
    return scoped_session(mem_session_factory)
