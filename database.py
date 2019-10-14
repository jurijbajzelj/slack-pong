import os
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager


@contextmanager
def get_session():
    """ Creates a context with an open SQLAlchemy session.
    """
    engine = create_engine(os.environ['SLACK_APP_PONG_DATABASE_URL'], convert_unicode=True)
    db_session = scoped_session(sessionmaker(autocommit=False, autoflush=True, bind=engine))
    yield db_session
    db_session.commit()
    db_session.close()

def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    import yourapplication.models
    Base.metadata.create_all(bind=engine)
