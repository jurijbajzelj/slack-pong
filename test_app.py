import requests
from models import Match


BASE_URL = 'http://localhost:5000'


def test_authorization(test_server):
    raw_data = b'token=123&team_id=456&team_domain=abc&channel_id=789&channel_name=ch_name&user_id=ABC'
    headers = {
        'X-Slack-Signature': 'v0=1a2eeb0ac2a8a562cc98047a50bef95639047e7d2aeb54cb5a88a40617dedb57',
        'X-Slack-Request-Timestamp': '1571051763'
    }
    response = requests.post(f'{BASE_URL}/won', data=raw_data, headers=headers)
    print(response.text)
    assert requests.post(f'{BASE_URL}/won', data=raw_data, headers=headers).status_code == 400  # bad request

    # change last digit of a timestamp
    headers.update({'X-Slack-Request-Timestamp': '1571051764'})
    assert requests.post(f'{BASE_URL}/won', data=raw_data, headers=headers).status_code == 401  # unauthorized


def test_db(prepare_db, db_session, test_server, monkeypatch):
    assert db_session.query(Match).count() == 0
