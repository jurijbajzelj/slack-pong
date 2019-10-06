from flask import Flask, request, jsonify
import requests
import json
import os
from database import db_session
from models import OAuth
import hmac
import hashlib


app = Flask(__name__)

CLIENT_ID = os.environ['SLACK_APP_PONG_CLIENT_ID']
CLIENT_SECRET = os.environ['SLACK_APP_PONG_CLIENT_SECRET']
SIGNING_SECRET = os.environ['SLACK_APP_PONG_SIGNING_SECRET']

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

@app.errorhandler(500)
def handle_internal_server_error(e):
    return 'HTTP 500', 500

@app.route("/")
def home():
    return "Hello, World!"

@app.route('/oauth', methods = ['GET'])
def oauth():
    code = request.args.get('code')
    if not code:
        return 'code missing', 500

    r = requests.get(url='https://slack.com/api/oauth.access', params={
        'code': code,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    })

    response = json.loads(r.text)

    oauth = OAuth(
        scope = response['scope'],
        enterprise_id = response['enterprise_id'],
        access_token = response['access_token'],
        team_id = response['team_id'],
        team_name = response['team_name'],
        user_id = response['user_id']
    )
    db_session.add(oauth)
    db_session.commit()

    return 'redirect somewhere'


@app.route("/command", methods = ['POST'])
def command():
    request_body = request.get_data().decode()
    x_slack_signature = request.headers['X-Slack-Signature']
    version = x_slack_signature.split('=')[0]
    x_slack_request_timestamp = request.headers['X-Slack-Request-Timestamp']

    sig_basestring = f'{version}:{x_slack_request_timestamp}:{request_body}'
    my_signature = hmac.new(SIGNING_SECRET.encode(), sig_basestring.encode(), hashlib.sha256).hexdigest()
    assert f'{version}={my_signature}' == x_slack_signature

    return "all good"

if __name__ == "__main__":
    app.run()
