from sqlalchemy import Column, Index, Integer, String, DateTime
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


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    slack_user_id = Column(String, nullable=False, index=True)
    nickname = Column(String, nullable=True)


class Match(Base):
    __tablename__ = 'match'

    id = Column(Integer, nullable=False, primary_key=True)
    winner = Column(String, nullable=False)
    loser = Column(String, nullable=False)
    team_id = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)


class UserContext(Base):
    """ Map external user context of Slack (combination of string ids) to internal one (integer id).
    """
    __tablename__ = 'user_context'

    id = Column(Integer, primary_key=True)
    slack_user_id = Column(String, nullable=False)
    slack_user_name = Column(String, nullable=False)
    slack_team_id = Column(String, nullable=False)

    __table_args__ = (
        Index('idx_user_context_0', 'slack_user_id', 'slack_team_id', unique=True),
        Index('idx_user_context_1', 'slack_user_name')
    )
