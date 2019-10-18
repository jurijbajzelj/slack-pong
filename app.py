from flask import Flask, request, jsonify, Response
from functools import wraps
import requests
import json
import os
from database import get_session
from models import OAuth, MatchOld, Team, Channel, AppUser, Match
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


def get_team(db, slack_team_id: str, slack_team_domain: str):
    assert isinstance(slack_team_id, str)
    assert isinstance(slack_team_domain, str)
    team = db.query(Team).filter(Team.slack_team_id == slack_team_id).first()
    if team:
        team.slack_team_domain = slack_team_domain
    else:
        team = Team(slack_team_id=slack_team_id, slack_team_domain=slack_team_domain)
        db.add(team)
        db.flush()
    return team


def get_channel(db, team_id: int, slack_channel_id: str, slack_channel_name: str):
    assert isinstance(team_id, int)
    assert isinstance(slack_channel_id, str)
    assert isinstance(slack_channel_name, str)
    channel = db.query(Channel).filter(Channel.team_id == team_id, Channel.slack_channel_id == slack_channel_id).first()
    if channel:
        channel.slack_channel_name = slack_channel_name
    else:
        channel = Channel(team_id=team_id, slack_channel_id=slack_channel_id, slack_channel_name=slack_channel_name)
        db.add(channel)
        db.flush()
    return channel


def get_app_user(db, team_id: int, slack_user_id: str, slack_user_name: str):
    assert isinstance(team_id, int)
    assert isinstance(slack_user_id, str)
    assert isinstance(slack_user_name, str)
    app_user = db.query(AppUser).filter(AppUser.team_id == team_id, AppUser.slack_user_id == slack_user_id).first()
    if app_user:
        app_user.slack_user_name = slack_user_name
    else:
        app_user = AppUser(team_id=team_id, slack_user_id=slack_user_id, slack_user_name=slack_user_name)
        db.add(app_user)
        db.flush()
    return app_user


def insert_match(db, channel_id: int, player_1_id: int, player_2_id: int, winner_id: id):
    assert isinstance(channel_id, int)
    assert isinstance(player_1_id, int)
    assert isinstance(player_2_id, int)
    assert isinstance(winner_id, int)
    timestamp = datetime.now().replace(microsecond=0)
    match = Match(channel_id=channel_id, player_1_id=player_1_id, player_2_id=player_2_id, winner_id=winner_id, timestamp=timestamp)
    db.add(match)
    return match


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
        name=db.query(AppUser).get(app_user_id).slack_user_name,  # TODO add support for nicknames
        elo=int(elo),
        played=matches_played[app_user_id],
        won=matches_won[app_user_id],
        lost=matches_lost[app_user_id]
    ) for app_user_id, elo in sorted_by_elo]


@app.route('/won', methods = ['POST'])
@authorize
def won():
    winner_slack_id = request.form['user_id']
    winner_slack_name = request.form['user_name']
    loser_slack_id = request.form['text'].strip().split('<@')[1].split('|')[0].split('>')[0]
    loser_slack_name = request.form['text'].strip().split('|')[1][:-1]
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
