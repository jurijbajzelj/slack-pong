from pytest import fixture
from database import get_session
from models import Base
from importlib import reload
import app


@fixture
def client(monkeypatch):
    with monkeypatch.context() as m:
        m.setenv('SLACK_APP_PONG_SIGNING_SECRET', '0'*66)
        m.setenv('SLACK_APP_PONG_DATABASE_URL', 'postgres://root:root@localhost:5432/circle-test_test')
        reload(app)
        return app.app.test_client()


@fixture
def db_session(client):
    with client.application.app_context():
        with get_session() as session:
            return session


@fixture
def prepare_db(db_session):
    Base.metadata.drop_all(bind=db_session.get_bind())
    Base.metadata.create_all(bind=db_session.get_bind())
