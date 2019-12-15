import json
import pytest

from undecorated import undecorated

from models import Match


@pytest.mark.usefixtures('prepare_db')
def test_authorize_validate(client, monkeypatch):
    headers = {
        'X-Slack-Signature': 'v0=1a42e11e6acd65647b826eed12be835247f0754f4a285f70a366d4a8472579da',
        'X-Slack-Request-Timestamp': '1571051763'
    }
    data = {
        'token': '123',
        'team_id': '456',
        'team_domain': 'abc',
        'channel_id': '789',
        'channel_name': 'ch_name',
        'user_id': 'ABC',
        'user_name': 'DEF',
        'text': 'some_text'
    }
    assert client.post('/reset', data=data, headers=headers).status_code == 200

    with monkeypatch.context() as m:  # change last digit of a timestamp
        m.setitem(headers, 'X-Slack-Request-Timestamp', '1571051764')
        assert client.post('/won', data=data, headers=headers).status_code == 401  # Unauthorized

    with monkeypatch.context() as m:
        m.delitem(data, 'user_name')  # this should case HTTP 400 response
        # modify signature so that request passes authorization stage
        m.setitem(headers, 'X-Slack-Signature', 'v0=ba48c2992cc5b2c964af29c50c242969860fbdf410c5502c0b7d3107eb059cef')
        assert client.post('/won', data=data, headers=headers).status_code == 400  # Bad Request


def test_db(prepare_db, db_session):
    assert db_session.query(Match).count() == 0


def undecorate(app, function: str):
    app.view_functions[function] = undecorated(app.view_functions[function])


def test_nickname(client):
    undecorate(client.application, 'nickname')
    assert client.post('/nickname').status_code == 400  # bad request


@pytest.mark.usefixtures('prepare_db')
def test_won(client):
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
        '[  ELO ] #. Name                       #↑/↓ | W | L | GP |  Win % | Streak'
        '--------------------------------------------------------------------------'
        '[ 1517 ] 1. gregor                          | 1 | 0 |  1 | 100.0% |       '
        '--------------------------------------------------------------------------'
        '[ 1485 ] 2. some_player_with_long_name      | 0 | 1 |  1 |   0.0% |       '
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
        '[  ELO ] #. Name                       #↑/↓ | W | L | GP |  Win % | Streak'
        '--------------------------------------------------------------------------'
        '[ 1517 ] 1. gregor                          | 1 | 0 |  1 | 100.0% |       '
        '--------------------------------------------------------------------------'
        '[ 1503 ] 2. some_player_with_long_name      | 1 | 1 |  2 |  50.0% |       '
        '--------------------------------------------------------------------------'
        '[ 1485 ] 3. yuri                            | 0 | 1 |  1 |   0.0% |       '
    )

    resp = client.post(
        '/won',
        data={
            'user_id': 'yuri_id',
            'user_name': 'yuri',
            'text': '<@gregor_id|gregor>',
            'team_id': 'team_1',
            'team_domain': 'some-team',
            'channel_id': 'channel_1',
            'channel_name': 'some-channel'
        }
    )
    assert resp.status_code == 200
    resp = json.loads(resp.get_data())['text'].strip('```').replace('\n', '')
    assert resp == (
        '[  ELO ] #. Name                       #↑/↓ | W | L | GP | Win % | Streak'
        '-------------------------------------------------------------------------'
        '[ 1503 ] 1. yuri                         2↑ | 1 | 1 |  2 | 50.0% |       '
        '-------------------------------------------------------------------------'
        '[ 1503 ] 2. some_player_with_long_name      | 1 | 1 |  2 | 50.0% |       '
        '-------------------------------------------------------------------------'
        '[ 1501 ] 3. gregor                       2↓ | 1 | 1 |  2 | 50.0% |       '
    )

    resp = client.post(
        '/won',
        data={
            'user_id': 'yuri_id',
            'user_name': 'yuri',
            'text': '<@gregor_id|gregor>',
            'team_id': 'team_1',
            'team_domain': 'some-team',
            'channel_id': 'channel_1',
            'channel_name': 'some-channel'
        }
    )
    assert resp.status_code == 200
    resp = json.loads(resp.get_data())['text'].strip('```').replace('\n', '')
    assert resp == (
        '[  ELO ] #. Name                       #↑/↓ | W | L | GP | Win % | Streak'
        '-------------------------------------------------------------------------'
        '[ 1520 ] 1. yuri                            | 2 | 1 |  3 | 66.7% |  2 Won'
        '-------------------------------------------------------------------------'
        '[ 1503 ] 2. some_player_with_long_name      | 1 | 1 |  2 | 50.0% |       '
        '-------------------------------------------------------------------------'
        '[ 1487 ] 3. gregor                          | 1 | 2 |  3 | 33.3% | 2 Lost'
    )
