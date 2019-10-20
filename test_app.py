from models import Match
from undecorated import undecorated


def test_authorization(client):
    raw_data = b'token=123&team_id=456&team_domain=abc&channel_id=789&channel_name=ch_name&user_id=ABC'
    headers = {
        'X-Slack-Signature': 'v0=1a2eeb0ac2a8a562cc98047a50bef95639047e7d2aeb54cb5a88a40617dedb57',
        'X-Slack-Request-Timestamp': '1571051763'
    }
    assert client.post('/won', data=raw_data, headers=headers).status_code == 400  # Bad Request

    # change last digit of a timestamp
    headers.update({'X-Slack-Request-Timestamp': '1571051764'})
    assert client.post('/won', data=raw_data, headers=headers).status_code == 401  # Unauthorized


def test_db(prepare_db, db_session):
    assert db_session.query(Match).count() == 0


def undecorate(app, function: str):
    app.view_functions[function] = undecorated(app.view_functions[function])


def test_nickname(client):
    undecorate(client.application, 'nickname')
    assert client.post('/nickname').status_code == 400  # bad request


def test_won(client):
    undecorate(client.application, 'won')
    assert client.post(
        '/won',
        data={
        }
    ).status_code == 400
