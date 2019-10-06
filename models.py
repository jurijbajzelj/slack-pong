from sqlalchemy import Column, Integer, String
from database import Base

class OAuth(Base):
    __tablename__ = 'oauth'

    id = Column(Integer, nullable=False, primary_key=True)
    scope = Column(String, nullable=False)
    enterprise_id = Column(String, nullable=True)
    access_token = Column(String, nullable=False)
    team_id = Column(String, nullable=False)
    team_name = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
