import pytest
import threading
import wsgiref.simple_server
from database import get_session
from models import Base
from app import app as my_app


@pytest.fixture
def test_server(monkeypatch):

    class ServerThread(threading.Thread):
        def run(self):
            self.httpd = wsgiref.simple_server.make_server('localhost', 5000, my_app)
            self.httpd.serve_forever()

        def stop(self):
            self.httpd.shutdown()

    with monkeypatch.context() as m:
        m.setenv('SLACK_APP_PONG_SIGNING_SECRET', '0'*66)
        server_thread = ServerThread()
        server_thread.start()
        yield server_thread
        server_thread.stop()
        server_thread.join()


@pytest.fixture
def prepare_db(monkeypatch):
    with monkeypatch.context() as m:
        m.setenv('SLACK_APP_PONG_DATABASE_URL', 'postgres://root:root@localhost:5432/circle-test_test')
        with get_session() as db_session:
            Base.metadata.drop_all(bind=db_session.get_bind())
            Base.metadata.create_all(bind=db_session.get_bind())


@pytest.fixture
def db_session(monkeypatch):
    with monkeypatch.context() as m:
        m.setenv('SLACK_APP_PONG_DATABASE_URL', 'postgres://root:root@localhost:5432/circle-test_test')
        with get_session() as session:
            return session
