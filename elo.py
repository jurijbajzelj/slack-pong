from typing import List
from models import Match, Channel


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

    def __init__(self, app_user_id, elo, played, lost, won):
        self.app_user_id = app_user_id
        self.elo = elo
        self.played = played
        self.lost = lost
        self.won = won
        self.win_percentage = int(won / played)

    def set_name(self, name: str):
        assert isinstance(name, str)
        self.name = name
        return self


def get_leaderboard(db, channel_id: int):
    match_list = db.query(Match).join(Channel).filter(
        Channel.id == channel_id,
        Match.timestamp >= Channel.rankings_reset_at
    ).all()

    player_ids = set(match.winner_id for match in match_list).union(match.loser_id for match in match_list)

    elo_dict = {player_id: 1500 for player_id in player_ids}
    matches_played = {player_id: 0 for player_id in player_ids}
    matches_won = {player_id: 0 for player_id in player_ids}
    matches_lost = {player_id: 0 for player_id in player_ids}

    for match in match_list:
        elo_dict[match.winner_id] = calculate_elo(
            old=elo_dict[match.winner_id],
            exp=calculate_expected(player_1_elo=elo_dict[match.winner_id], player_2_elo=elo_dict[match.loser_id]),
            score=1
        )
        elo_dict[match.loser_id] = calculate_elo(
            old=elo_dict[match.loser_id],
            exp=calculate_expected(player_1_elo=elo_dict[match.loser_id], player_2_elo=elo_dict[match.winner_id]),
            score=0
        )
        matches_played[match.winner_id] += 1
        matches_played[match.loser_id] += 1
        matches_won[match.winner_id] += 1
        matches_lost[match.loser_id] += 1

    # for every match played, player is granted +1 bonus points
    for player_id, elo in elo_dict.items():
        elo_dict[player_id] = elo + matches_played[player_id]

    sorted_by_elo = sorted(elo_dict.items(), key=lambda kv: kv[1], reverse=True)
    return [PlayerStats(
        app_user_id=app_user_id,
        elo=int(elo),
        played=matches_played[app_user_id],
        won=matches_won[app_user_id],
        lost=matches_lost[app_user_id]
    ) for app_user_id, elo in sorted_by_elo]
