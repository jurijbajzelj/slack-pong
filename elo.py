from typing import List
from models import Match


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


def get_leaderboard(match_list: List[Match]):
    assert isinstance(match_list, list)

    player_ids = set(match.player_1_id for match in match_list).union(match.player_2_id for match in match_list)

    elo_dict = {player_id: 1500 for player_id in player_ids}
    matches_played = {player_id: 0 for player_id in player_ids}
    matches_won = {player_id: 0 for player_id in player_ids}
    matches_lost = {player_id: 0 for player_id in player_ids}

    for match in match_list:
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
        app_user_id=app_user_id,
        elo=int(elo),
        played=matches_played[app_user_id],
        won=matches_won[app_user_id],
        lost=matches_lost[app_user_id]
    ) for app_user_id, elo in sorted_by_elo]
