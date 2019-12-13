from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Index
from sqlalchemy.ext import declarative


Base = declarative.declarative_base()


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
    rankings_reset_at = Column(DateTime, nullable=False)


class Match(Base):
    __tablename__ = 'match'

    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, ForeignKey('channel.id', ondelete='CASCADE'), nullable=False)
    winner_id = Column(Integer, ForeignKey('app_user.id', ondelete='CASCADE'), nullable=False)
    loser_id = Column(Integer, ForeignKey('app_user.id', ondelete='CASCADE'), nullable=False)
    timestamp = Column(DateTime, nullable=False)

    __table_args__ = (
        Index('idx_match_0', 'id', 'timestamp'),  # used withing get_leaderboard function
    )
