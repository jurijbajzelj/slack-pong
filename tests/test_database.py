import pytest
from database import get_session, get_channel
from models import Channel, Team


@pytest.mark.usefixtures('prepare_db')
@pytest.mark.freeze_time('4 dec 2019 16:34:15.123456')
def test_get_channel_rankings_reset_at_default_value():
    with get_session() as db:
        db.add(Team(slack_team_id=1, slack_team_domain='test.com'))
        db.flush()
        channel = get_channel(db, team_id=1, slack_channel_id='a', slack_channel_name='b')
        db.commit()
        assert str(channel.rankings_reset_at) == '2019-12-04 16:34:15'
