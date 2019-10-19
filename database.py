import os
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
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
