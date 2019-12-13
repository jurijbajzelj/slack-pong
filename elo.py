from collections import defaultdict
from copy import deepcopy
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
    return old + k * (score - exp) + 1  # for every match played, player is granted +1 bonus points


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


def update_state(match: Match, elo: dict, played: dict, won: dict, lost: dict):
    elo[match.winner_id] = calculate_elo(
        old=elo[match.winner_id],
        exp=calculate_expected(player_1_elo=elo[match.winner_id], player_2_elo=elo[match.loser_id]),
        score=1
    )
    elo[match.loser_id] = calculate_elo(
        old=elo[match.loser_id],
        exp=calculate_expected(player_1_elo=elo[match.loser_id], player_2_elo=elo[match.winner_id]),
        score=0
    )
    played[match.winner_id] += 1
    played[match.loser_id] += 1
    won[match.winner_id] += 1
    lost[match.loser_id] += 1


def get_leaderboard(db, channel_id: int):
    match_list = db.query(Match).join(Channel).filter(
        Channel.id == channel_id,
        Match.timestamp >= Channel.rankings_reset_at
    ).all()

    elo = defaultdict(lambda: 1500)
    played = defaultdict(lambda: 0)
    won = defaultdict(lambda: 0)
    lost = defaultdict(lambda: 0)
    for match in match_list[:-1]:
        update_state(match=match, elo=elo, played=played, won=won, lost=lost)

    elo_new = deepcopy(elo)
    played_new = deepcopy(played)
    won_new = deepcopy(won)
    lost_new = deepcopy(lost)
    if match_list:
        update_state(match=match_list[-1], elo=elo_new, played=played_new, won=won_new, lost=lost_new)

    sorted_by_elo = sorted(elo_new.items(), key=lambda kv: kv[1], reverse=True)
    return [PlayerStats(
        app_user_id=app_user_id,
        elo=int(elo),
        played=played_new[app_user_id],
        won=won_new[app_user_id],
        lost=lost_new[app_user_id]
    ) for app_user_id, elo in sorted_by_elo]
