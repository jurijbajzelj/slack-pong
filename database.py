from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from contextlib import contextmanager
from models import AppUser, Team, Channel, Match
from datetime import datetime
from flask import current_app


@contextmanager
def get_session():
    """ Creates a context with an open SQLAlchemy session.
    """
    engine = create_engine(current_app.config['DATABASE_URL'])
    db_session = scoped_session(sessionmaker(autocommit=False, autoflush=True, bind=engine))
    yield db_session
    db_session.commit()
    db_session.close()


def get_display_name(db, app_user_id: int):
    assert isinstance(app_user_id, int)
    app_user = db.query(AppUser).get(app_user_id)
    return app_user.nickname or app_user.slack_user_name


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
    match = Match(
        channel_id=channel_id,
        player_1_id=player_1_id,
        player_2_id=player_2_id,
        winner_id=winner_id,
        timestamp=timestamp
    )
    db.add(match)
    return match
