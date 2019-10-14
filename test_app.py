import requests


BASE_URL = 'http://localhost:5000'


def test_authorization(test_server):
    raw_data = b'token=123&team_id=456&team_domain=abc&channel_id=789&channel_name=ch_name&user_id=ABC'
    headers = {
        'X-Slack-Signature': 'v0=2ffc0f6a85aa4bfe76c5d03af3d07cf09ac730431957e494693e0ad445c6f267',
        'X-Slack-Request-Timestamp': '1571051763'
    }
    assert requests.post(f'{BASE_URL}/won', data=raw_data, headers=headers).status_code == 400  # bad request

    # change last digit of a timestamp
    headers.update({'X-Slack-Request-Timestamp': '1571051764'})
    assert requests.post(f'{BASE_URL}/won', data=raw_data, headers=headers).status_code == 401  # unauthorized
