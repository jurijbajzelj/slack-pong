import pytest
from elo import get_leaderboard
from datetime import datetime, timedelta
from database import get_session
from models import Match, Channel, Team, AppUser


@pytest.mark.usefixtures('prepare_db')
def test_get_leaderboard():
    with get_session() as db:
        now = datetime.utcnow().replace(microsecond=0)
        assert get_leaderboard(db=db, channel_id=1) == []

        db.add(Team(slack_team_id='a', slack_team_domain='test.com')); db.flush()
        db.add(Channel(team_id=1, slack_channel_id='b', slack_channel_name='c', rankings_reset_at=now)); db.flush()
        db.add(AppUser(team_id=1, slack_user_id='p_1', slack_user_name='u_1')); db.flush()
        db.add(AppUser(team_id=1, slack_user_id='p_2', slack_user_name='u_2')); db.flush()
        db.add(AppUser(team_id=1, slack_user_id='p_3', slack_user_name='u_3')); db.flush()
        db.add(Match(channel_id=1, player_1_id=1, player_2_id=2, winner_id=1, timestamp=now)); db.flush()
        db.add(Match(channel_id=1, player_1_id=1, player_2_id=3, winner_id=1, timestamp=now)); db.flush()
        assert [el.__dict__ for el in get_leaderboard(db=db, channel_id=1)] == [
            {'app_user_id': 1, 'elo': 1533, 'played': 2, 'lost': 0, 'won': 2, 'win_percentage': 1},
            {'app_user_id': 3, 'elo': 1486, 'played': 1, 'lost': 1, 'won': 0, 'win_percentage': 0},
            {'app_user_id': 2, 'elo': 1485, 'played': 1, 'lost': 1, 'won': 0, 'win_percentage': 0}
        ]

        db.query(Match).get(1).timestamp = now - timedelta(seconds=1)
        db.flush()
        assert [el.__dict__ for el in get_leaderboard(db=db, channel_id=1)] == [
            {'app_user_id': 1, 'elo': 1517, 'played': 1, 'lost': 0, 'won': 1, 'win_percentage': 1},
            {'app_user_id': 3, 'elo': 1485, 'played': 1, 'lost': 1, 'won': 0, 'win_percentage': 0}
        ]
