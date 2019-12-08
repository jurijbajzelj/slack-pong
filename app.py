from flask import Flask, request
from functools import wraps
import requests
import json
import os
from database import get_session, get_display_name, get_team, get_channel, get_app_user, insert_match
from models import OAuth
import hmac
import hashlib
from elo import get_leaderboard, PlayerStats
from types import SimpleNamespace
from typing import List
from datetime import datetime

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

SENTRY_DSN = os.getenv('SLACK_APP_PONG_SENTRY_DSN')  # should not be configured when test are running
sentry_sdk.init(
    dsn=SENTRY_DSN,
    integrations=[FlaskIntegration(), SqlalchemyIntegration()]
) if SENTRY_DSN else None

app = Flask(__name__)

app.config['DATABASE_URL'] = os.environ['SLACK_APP_PONG_DATABASE_URL']
app.config['SIGNING_SECRET'] = os.environ['SLACK_APP_PONG_SIGNING_SECRET']

CLIENT_ID = os.environ['SLACK_APP_PONG_CLIENT_ID']
CLIENT_SECRET = os.environ['SLACK_APP_PONG_CLIENT_SECRET']


class AuthorizeException(Exception):
    pass


class ValidateException(Exception):
    pass


class TimeoutException(Exception):
    pass


@app.errorhandler(500)
def handle_internal_server_error(e):
    if isinstance(e.original_exception, TimeoutException):
        sentry_sdk.capture_exception(e)
        return {
            'response_type': 'in_channel',
            'text': '`Looks like the server is taking to long to respond, please try again.`'
        }
    elif isinstance(e.original_exception, ValidateException):
        sentry_sdk.capture_exception(e)
        return 'Bad Request', 400
    elif isinstance(e.original_exception, AuthorizeException):
        sentry_sdk.capture_exception(e)
        return 'Unauthorized', 401
    return 'Internal Server Error', 500


@app.route('/oauth', methods=['GET'])
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
            scope=response['scope'],
            enterprise_id=response['enterprise_id'],
            access_token=response['access_token'],
            team_id=response['team_id'],
            team_name=response['team_name'],
            user_id=response['user_id']
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
                app.config['SIGNING_SECRET'].encode(),
                sig_basestring.encode(),
                hashlib.sha256
            ).hexdigest()
            assert f'{version}={my_signature}' == x_slack_signature
        except Exception:
            raise AuthorizeException(request.headers, request.form)
        return f(*args, **kwargs)
    return wrapper


def validate(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            for field in ['user_id', 'user_name', 'text', 'team_id', 'team_domain', 'channel_id', 'channel_name']:
                assert field in request.form and isinstance(request.form[field], str)
        except Exception:
            raise ValidateException(request.form)
        return f(*args, **kwargs)
    return wrapper


@app.route('/nickname', methods=['POST'])
@authorize
def nickname():
    # TODO limit length, validation, also tests
    # TODO make it clear that this command is available
    with get_session() as db:
        team = get_team(db=db, slack_team_id=request.form['team_id'], slack_team_domain=request.form['team_domain'])
        app_user = get_app_user(db=db, team_id=team.id, slack_user_id=request.form['user_id'],
                                slack_user_name=request.form['user_name'])
        app_user.nickname = request.form['text']
        return {
            'response_type': 'in_channel',
            'text': f'<@{app_user.slack_user_id}> changed his nickname to _{app_user.nickname}_'
        }


@app.route('/won', methods=['POST'])
@authorize
@validate
def won():
    # validate the command text
    winner_slack_id = request.form['user_id']
    try:
        loser_slack_id = request.form['text'].strip().split('<@')[1].split('|')[0].split('>')[0]
        loser_slack_name = request.form['text'].strip().split('|')[1][:-1]
    except Exception:
        return {
            'text': ':x: You should mention someone when reporting a win, like this:',
            'attachments': [{
                'text': f'`/won <@{winner_slack_id}>` _(but don\'t mention yourself, this is just an example)_'
            }]
        }

    # check that mentioned player is not the one reporting the win
    if winner_slack_id == loser_slack_id:
        return {
            'text': ':x: You cannot mention yourself. Mention the player you have won.'
        }

    winner_slack_name = request.form['user_name']
    team_id = request.form['team_id']
    team_domain = request.form['team_domain']
    channel_id = request.form['channel_id']
    channel_name = request.form['channel_name']

    with get_session() as db:
        team = get_team(db, slack_team_id=team_id, slack_team_domain=team_domain)
        channel = get_channel(db, team_id=team.id, slack_channel_id=channel_id, slack_channel_name=channel_name)
        winner = get_app_user(db, team_id=team.id, slack_user_id=winner_slack_id, slack_user_name=winner_slack_name)
        loser = get_app_user(db, team_id=team.id, slack_user_id=loser_slack_id, slack_user_name=loser_slack_name)
        insert_match(db, channel_id=channel.id, winner_id=winner.id, loser_id=loser.id)

        def get_leaderboard_lines(db, leaderboard: List[PlayerStats]):
            updated_leaderboard = [x.set_name(get_display_name(db=db, app_user_id=x.app_user_id)) for x in leaderboard]
            longest = SimpleNamespace(**{
                'elo': len('ELO'),
                'counter': len(str(len(leaderboard))),
                'name': len('Name'),
                'won': len('Won'),
                'lost': len('Lost')
            })
            for x in updated_leaderboard:
                longest.elo = max(longest.elo, len(str(x.elo)))
                longest.name = max(longest.name, len(str(x.name)))
                longest.won = max(longest.won, len(str(x.won)))
                longest.lost = max(longest.lost, len(str(x.lost)))

            lines = []
            elo = 'ELO'[:longest.elo].rjust(longest.elo)
            counter = '#'[:longest.counter].rjust(longest.counter)
            name = 'Name'[:longest.name].ljust(longest.name)
            won = 'Won'[:longest.won].rjust(longest.won)
            lost = 'Lost'[:longest.lost].rjust(longest.lost)
            lines.append(f'[ {elo} ] {counter}. {name} {won} {lost}')
            for i, x in enumerate(updated_leaderboard, start=1):
                elo = str(x.elo)[:longest.elo].rjust(longest.elo)
                counter = str(i)[:longest.counter].rjust(longest.counter)
                name = x.name[:longest.name].ljust(longest.name)
                won = str(x.won)[:longest.won].rjust(longest.won)
                lost = str(x.lost)[:longest.lost].rjust(longest.lost)
                lines.append(f'[ {elo} ] {counter}. {name} {won} {lost}')
            return lines

        leaderboard = get_leaderboard(db=db, channel_id=channel.id)
        leaderboard_lines = get_leaderboard_lines(db=db, leaderboard=leaderboard)
        return {
            'response_type': 'in_channel',
            'text': '```' + '\n'.join(leaderboard_lines) + '```'
        }


@app.route('/reset', methods=['POST'])
@authorize
@validate
def reset():
    team_id = request.form['team_id']
    team_domain = request.form['team_domain']
    channel_id = request.form['channel_id']
    channel_name = request.form['channel_name']

    with get_session() as db:
        team = get_team(db=db, slack_team_id=team_id, slack_team_domain=team_domain)
        channel = get_channel(db=db, team_id=team.id, slack_channel_id=channel_id, slack_channel_name=channel_name)
        channel.rankings_reset_at = datetime.utcnow().replace(microsecond=0)

    return {
        'response_type': 'in_channel',
        'text': 'Rankings reset for this channel.'
    }


if __name__ == "__main__":
    app.run()
