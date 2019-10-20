from abc import abstractmethod
from flask import Flask, request
from functools import wraps
import requests
import json
import os
from database import get_session, get_display_name, get_team, get_channel, get_app_user, insert_match
from models import OAuth, Match
import hmac
import hashlib
from threading import Thread


app = Flask(__name__)

app.config['DATABASE_URL'] = os.environ['SLACK_APP_PONG_DATABASE_URL']
app.config['SIGNING_SECRET'] = os.environ['SLACK_APP_PONG_SIGNING_SECRET']

CLIENT_ID = os.environ['SLACK_APP_PONG_CLIENT_ID']
CLIENT_SECRET = os.environ['SLACK_APP_PONG_CLIENT_SECRET']


class AuthorizeException(Exception):
    pass


class ValidateException(Exception):
    pass


@app.errorhandler(500)
def handle_internal_server_error(e):
    if isinstance(e.original_exception, ValidateException):
        return 'Bad Request', 400
    elif isinstance(e.original_exception, AuthorizeException):
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


def calculate_expected(player_1_elo, player_2_elo):
    """
    Calculate expected score of A in a match against B
    :param A: Elo rating for player A
    :param B: Elo rating for player B
    """
    return 1 / (1 + 10 ** ((player_2_elo - player_1_elo) / 400))


def calculate_elo(old, exp, score, k=32):
    """
    Calculate the new Elo rating for a player
    :param old: The previous Elo rating
    :param exp: The expected score for this match
    :param score: The actual score for this match
    :param k: The k-factor for Elo (default: 32)
    """
    return old + k * (score - exp)


class PlayerStats:

    def __init__(self, name, elo, played, lost, won):
        self.name = name
        self.elo = elo
        self.played = played
        self.lost = lost
        self.won = won
        self.win_percentage = int(won / played)


def get_leaderboard(db, channel_id: int):
    assert isinstance(channel_id, int)
    # load all player ids for all matches in the channel
    group_1 = db.query(Match.player_1_id).filter(Match.channel_id == channel_id).group_by(Match.player_1_id)
    group_1_set = set(player_id for player_id, in group_1)
    group_2 = db.query(Match.player_2_id).filter(Match.channel_id == channel_id).group_by(Match.player_2_id)
    group_2_set = set(player_id for player_id, in group_2)
    player_ids = group_1_set.union(group_2_set)

    elo_dict = {player_id: 1500 for player_id in player_ids}
    matches_played = {player_id: 0 for player_id in player_ids}
    matches_won = {player_id: 0 for player_id in player_ids}
    matches_lost = {player_id: 0 for player_id in player_ids}

    for match in db.query(Match).filter(Match.channel_id == channel_id):
        elo_dict[match.player_1_id] = calculate_elo(
            old=elo_dict[match.player_1_id],
            exp=calculate_expected(player_1_elo=elo_dict[match.player_1_id], player_2_elo=elo_dict[match.player_2_id]),
            score=int(match.player_1_id == match.winner_id)
        )
        elo_dict[match.player_2_id] = calculate_elo(
            old=elo_dict[match.player_2_id],
            exp=calculate_expected(player_1_elo=elo_dict[match.player_2_id], player_2_elo=elo_dict[match.player_1_id]),
            score=int(match.player_2_id == match.winner_id)
        )
        matches_played[match.player_1_id] += 1
        matches_played[match.player_2_id] += 1
        if match.player_1_id == match.winner_id:
            matches_won[match.player_1_id] += 1
            matches_lost[match.player_2_id] += 1
        if match.player_2_id == match.winner_id:
            matches_won[match.player_2_id] += 1
            matches_lost[match.player_1_id] += 1

    for player_id, elo in elo_dict.items():
        elo_dict[player_id] = elo + matches_played[player_id]

    sorted_by_elo = sorted(elo_dict.items(), key=lambda kv: kv[1], reverse=True)
    return [PlayerStats(
        name=get_display_name(db=db, app_user_id=app_user_id),
        elo=int(elo),
        played=matches_played[app_user_id],
        won=matches_won[app_user_id],
        lost=matches_lost[app_user_id]
    ) for app_user_id, elo in sorted_by_elo]


class AppThread(Thread):
    def __init__(self, request):
        Thread.__init__(self)
        self.request = request

    @abstractmethod
    def run(self):
        """ not implemented """


class NicknameThread(AppThread):

    def run(self):
        with app.app_context():
            with get_session() as db:
                team = get_team(
                    db=db,
                    slack_team_id=self.request.form['team_id'],
                    slack_team_domain=self.request.form['team_domain']
                )
                app_user = get_app_user(
                    db=db,
                    team_id=team.id,
                    slack_user_id=self.request.form['user_id'],
                    slack_user_name=self.request.form['user_name']
                )
                app_user.nickname = self.request.form['text']

                assert requests.post(
                    self.request.form['response_url'],
                    data=json.dumps({
                        'response_type': 'in_channel',
                        'text': f'<@{app_user.slack_user_id}> changed his nickname to _{app_user.nickname}_'
                    }),
                    headers={
                        'Content-Type': 'application/json'
                    }
                ).status_code == 200


@app.route('/nickname', methods=['POST'])
@authorize
def nickname():
    # TODO limit length, validation, also tests
    # TODO make it clear that this command is available
    NicknameThread(request.__copy__()).start()
    return f':heavy_check_mark: Your nickname will be changed to _{request.form["text"]}_', 200


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
        insert_match(db, channel_id=channel.id, player_1_id=winner.id, player_2_id=loser.id, winner_id=winner.id)

        counter = 0
        lines = []
        for p in get_leaderboard(db, channel_id=channel.id):
            counter += 1
            line = f'[ {p.elo} ] {counter}. {p.name} (W/L: {p.won}/{p.lost})'
            lines.append(line)
        text = '```' + '\n'.join(lines) + '```'

        return {
            'response_type': 'in_channel',
            'text': text
        }


if __name__ == "__main__":
    app.run()
