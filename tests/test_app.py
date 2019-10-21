from models import Match
from undecorated import undecorated
import json


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


def test_won(prepare_db, client):
    # TODO do this test also when migration to thread is done
    undecorate(client.application, 'won')

    resp = client.post(
        '/won',
        data={
            'user_id': 'gregor_id',
            'user_name': 'gregor',
            'text': '<@some_player_id|some_player_with_long_name>',
            'team_id': 'team_1',
            'team_domain': 'some-team',
            'channel_id': 'channel_1',
            'channel_name': 'some-channel'
        }
    )
    assert resp.status_code == 200
    resp = json.loads(resp.get_data())['text'].strip('```').replace('\n', '')
    assert resp == (
        '[  ELO ] #. Name                       Won Lost'
        '[ 1517 ] 1. gregor                       1    0'
        '[ 1485 ] 2. some_player_with_long_name   0    1'
    )

    resp = client.post(
        '/won',
        data={
            'user_id': 'some_player_id',
            'user_name': 'some_player_with_long_name',
            'text': '<@yuri_id|yuri>',
            'team_id': 'team_1',
            'team_domain': 'some-team',
            'channel_id': 'channel_1',
            'channel_name': 'some-channel'
        }
    )
    assert resp.status_code == 200
    resp = json.loads(resp.get_data())['text'].strip('```').replace('\n', '')
    assert resp == (
        '[  ELO ] #. Name                       Won Lost'
        '[ 1517 ] 1. gregor                       1    0'
        '[ 1503 ] 2. some_player_with_long_name   1    1'
        '[ 1485 ] 3. yuri                         0    1'
    )
