import pytest
from app import app as my_app
import threading
import wsgiref.simple_server


class ServerThread(threading.Thread):
    def run(self):
        self.httpd = wsgiref.simple_server.make_server('localhost', 5000, my_app)
        self.httpd.serve_forever()

    def stop(self):
        self.httpd.shutdown()

@pytest.fixture
def test_server():
    server_thread = ServerThread()
    server_thread.start()
    yield server_thread
    server_thread.stop()
    server_thread.join()
