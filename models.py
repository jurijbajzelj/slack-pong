from sqlalchemy import Column, ForeignKey, Index, Integer, String, DateTime
from sqlalchemy.ext import declarative


Base = declarative.declarative_base()


class OAuth(Base):
    __tablename__ = 'oauth'

    id = Column(Integer, nullable=False, primary_key=True)
    scope = Column(String, nullable=False)
    enterprise_id = Column(String, nullable=True)
    access_token = Column(String, nullable=False)
    team_id = Column(String, nullable=False)
    team_name = Column(String, nullable=False)
    user_id = Column(String, nullable=False)


class MatchOld(Base):
    __tablename__ = 'match_old'

    id = Column(Integer, nullable=False, primary_key=True)
    winner = Column(String, nullable=False)
    loser = Column(String, nullable=False)
    team_id = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)


class Team(Base):
    __tablename__ = 'team'

    id = Column(Integer, primary_key=True)
    slack_team_id = Column(String, nullable=False, unique=True)
    slack_team_domain = Column(String, nullable=False)


class AppUser(Base):
    __tablename__ = 'app_user'

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('team.id', ondelete='CASCADE'), nullable=False)
    slack_user_id = Column(String, nullable=False)
    slack_user_name = Column(String, nullable=False)
    nickname = Column(String)


class Channel(Base):
    __tablename__ = 'channel'

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('team.id', ondelete='CASCADE'), nullable=False)
    slack_channel_id = Column(String, nullable=False)
    slack_channel_name = Column(String, nullable=False)


class Match(Base):
    __tablename__ = 'match'

    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, ForeignKey('channel.id', ondelete='CASCADE'), nullable=False)
    player_1_id = Column(Integer, ForeignKey('app_user.id', ondelete='CASCADE'), nullable=False)
    player_2_id = Column(Integer, ForeignKey('app_user.id', ondelete='CASCADE'), nullable=False)
    winner_id = Column(Integer, ForeignKey('app_user.id', ondelete='CASCADE'), nullable=False)
    timestamp = Column(DateTime, nullable=False)
