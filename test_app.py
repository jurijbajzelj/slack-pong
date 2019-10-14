import requests


BASE_URL = 'http://localhost:5000'


def test_authorization(test_server, monkeypatch):
    with monkeypatch.context() as m:
        m.setenv('SLACK_APP_PONG_SIGNING_SECRET', '0'*66)
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
