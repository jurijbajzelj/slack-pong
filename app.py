from flask import Flask, request, jsonify, Response
from functools import wraps
import requests
import json
import os
from database import get_session
from models import OAuth, Match
import hmac
import hashlib
from datetime import datetime


app = Flask(__name__)

CLIENT_ID = os.environ['SLACK_APP_PONG_CLIENT_ID']
CLIENT_SECRET = os.environ['SLACK_APP_PONG_CLIENT_SECRET']
assert 'SLACK_APP_PONG_SIGNING_SECRET' in os.environ
assert 'SLACK_APP_PONG_DATABASE_URL' in os.environ

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

    with get_session() as db_session:
        oauth = OAuth(
            scope = response['scope'],
            enterprise_id = response['enterprise_id'],
            access_token = response['access_token'],
            team_id = response['team_id'],
            team_name = response['team_name'],
            user_id = response['user_id']
        )
        db_session.add(oauth)

    return 'redirect somewhere'


def authorize(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            request_body = request.get_data().decode()
            x_slack_signature = request.headers['X-Slack-Signature']
            version = x_slack_signature.split('=')[0]
            x_slack_request_timestamp = request.headers['X-Slack-Request-Timestamp']
            sig_basestring = f'{version}:{x_slack_request_timestamp}:{request_body}'
            my_signature = hmac.new(
                os.environ['SLACK_APP_PONG_SIGNING_SECRET'].encode(),
                sig_basestring.encode(),
                hashlib.sha256
            ).hexdigest()
            assert f'{version}={my_signature}' == x_slack_signature
        except:
            return Response('Unauthorized', 401)
        return f(*args, **kwargs)
    return wrapper


@app.route('/won', methods = ['POST'])
@authorize
def won():
    winner = request.form['user_id']
    loser = request.form['text'].strip().split('<@')[1].split('|')[0].split('>')[0]
    team_id = request.form['team_id']
    timestamp = datetime.now().replace(microsecond=0)

    with get_session() as db_session:
        match = Match(winner=winner, loser=loser, team_id=team_id, timestamp=timestamp)
        db_session.add(match)

        match_history = {}
        for match in db_session.query(Match).filter(Match.team_id == team_id):
            # insert default values
            if match.winner not in match_history:
                match_history[match.winner] = {
                    'wins': 0,
                    'losses': 0
                }
            if match.loser not in match_history:
                match_history[match.loser] = {
                    'wins': 0,
                    'losses': 0
                }
            match_history[match.winner]['wins'] += 1
            match_history[match.loser]['losses'] += 1
        # calculate percentage
        percentages = {}
        for key, value in match_history.items():
            percentages[key] = int(value['wins'] / (value['wins'] + value['losses']) * 100)

        sorted_percentages = sorted(percentages.items(), key=lambda kv: kv[1], reverse=True)

        output = ''
        for user, win_percentage in sorted_percentages:
            output += f"\n<@{user}> win percentage {win_percentage}% (W: {match_history[user]['wins']} L: {match_history[user]['losses']})"

        response = {
            'response_type': 'in_channel',
            'text': f"<@{winner}> reported a win over <@{loser}>",
            'attachments': [{
                'text': f'```Current standings\n{output}```'
            }]
        }
        return response

if __name__ == "__main__":
    app.run()
