"""
OFC Pineapple scoring: royalties, head-to-head comparison, Fantasyland.

Scoring rules (standard):
  - Each row won:  +1 point
  - Each row lost: -1 point
  - Scoop bonus:   +3 points (all 3 rows won)
  - Fouled hand:   lose all rows + opponent gets royalties + 6 penalty
  - Royalties:     bonus points for strong hands in specific rows
"""

from __future__ import annotations

from ofc.board import OFCBoard, Row
from ofc.card import card_rank
from ofc.evaluator import (
    HAND_FLUSH,
    HAND_FOUR_KIND,
    HAND_FULL_HOUSE,
    HAND_ONE_PAIR,
    HAND_ROYAL_FLUSH,
    HAND_STRAIGHT,
    HAND_STRAIGHT_FLUSH,
    HAND_THREE_KIND,
    HAND_TWO_PAIR,
    FRONT_ONE_PAIR,
    FRONT_THREE_KIND,
    compare_3,
    compare_5,
    evaluate_3,
    evaluate_5,
)

# ---------------------------------------------------------------------------
# Royalty tables
# ---------------------------------------------------------------------------

# Back row royalties (standard scoring)
BACK_ROYALTIES = {
    HAND_STRAIGHT: 2,
    HAND_FLUSH: 4,
    HAND_FULL_HOUSE: 6,
    HAND_FOUR_KIND: 10,
    HAND_STRAIGHT_FLUSH: 15,
    HAND_ROYAL_FLUSH: 25,
}

# Middle row royalties (double the back)
MIDDLE_ROYALTIES = {
    HAND_THREE_KIND: 2,
    HAND_STRAIGHT: 4,
    HAND_FLUSH: 8,
    HAND_FULL_HOUSE: 12,
    HAND_FOUR_KIND: 20,
    HAND_STRAIGHT_FLUSH: 30,
    HAND_ROYAL_FLUSH: 50,
}

# Front row pair royalties: pair of 6s+ earns royalties
# Pair of 6s = 1, 7s = 2, ..., As = 9
# Trips: 22 = 10, 33 = 11, ..., AA = 22
FRONT_PAIR_ROYALTIES = {
    4: 1,   # 6s
    5: 2,   # 7s
    6: 3,   # 8s
    7: 4,   # 9s
    8: 5,   # Ts
    9: 6,   # Js
    10: 7,  # Qs
    11: 8,  # Ks
    12: 9,  # As
}

FRONT_TRIP_BASE_ROYALTY = 10  # Trips of 2s = 10, 3s = 11, ..., As = 22


# ---------------------------------------------------------------------------
# Royalty calculation
# ---------------------------------------------------------------------------

def royalties_back(cards: list[int]) -> int:
    """Calculate royalties for the back row (5 cards)."""
    if len(cards) != 5:
        return 0
    hand_class, _ = evaluate_5(cards)
    return BACK_ROYALTIES.get(hand_class, 0)


def royalties_middle(cards: list[int]) -> int:
    """Calculate royalties for the middle row (5 cards)."""
    if len(cards) != 5:
        return 0
    hand_class, _ = evaluate_5(cards)
    return MIDDLE_ROYALTIES.get(hand_class, 0)


def royalties_front(cards: list[int]) -> int:
    """Calculate royalties for the front row (3 cards)."""
    if len(cards) != 3:
        return 0
    hand_class, rank_value = evaluate_3(cards)

    if hand_class == FRONT_THREE_KIND:
        trip_rank = rank_value  # The trip rank (0=2, 12=A)
        return FRONT_TRIP_BASE_ROYALTY + trip_rank

    if hand_class == FRONT_ONE_PAIR:
        pair_rank = rank_value // 13  # Extract pair rank
        return FRONT_PAIR_ROYALTIES.get(pair_rank, 0)

    return 0


def total_royalties(board: OFCBoard) -> int:
    """Calculate total royalties for a complete board."""
    if not board.is_complete():
        return 0
    if board.is_fouled():
        return 0  # Fouled boards earn no royalties
    return (
        royalties_front(board.front)
        + royalties_middle(board.middle)
        + royalties_back(board.back)
    )


# ---------------------------------------------------------------------------
# Head-to-head scoring
# ---------------------------------------------------------------------------

def score_head_to_head(my_board: OFCBoard, opp_board: OFCBoard) -> int:
    """Score my board against opponent's board.

    Returns the net points I earn (negative if I lose).
    Both boards must be complete.
    """
    assert my_board.is_complete() and opp_board.is_complete()

    my_fouled = my_board.is_fouled()
    opp_fouled = opp_board.is_fouled()

    # Both fouled: no points exchanged, no royalties
    if my_fouled and opp_fouled:
        return 0

    # I fouled, opponent didn't: I lose 6 + opponent's royalties
    if my_fouled:
        return -(6 + total_royalties(opp_board))

    # Opponent fouled: I win 6 + my royalties
    if opp_fouled:
        return 6 + total_royalties(my_board)

    # Neither fouled: row-by-row comparison
    score = 0

    # Front row (3-card comparison)
    front_result = compare_3(my_board.front, opp_board.front)
    # Middle row (5-card comparison)
    middle_result = compare_5(my_board.middle, opp_board.middle)
    # Back row (5-card comparison)
    back_result = compare_5(my_board.back, opp_board.back)

    rows_won = sum(1 for r in [front_result, middle_result, back_result] if r > 0)
    rows_lost = sum(1 for r in [front_result, middle_result, back_result] if r < 0)

    # +1 per row won, -1 per row lost
    score += rows_won - rows_lost

    # Scoop bonus: +3 if all 3 rows won
    if rows_won == 3:
        score += 3
    elif rows_lost == 3:
        score -= 3

    # Add royalty difference
    score += total_royalties(my_board) - total_royalties(opp_board)

    return score


# ---------------------------------------------------------------------------
# Fantasyland
# ---------------------------------------------------------------------------

def qualifies_fantasyland(board: OFCBoard) -> bool:
    """Check if a complete board qualifies for Fantasyland.

    Standard rule: QQ or better in front row.
    """
    if not board.is_complete() or board.is_fouled():
        return False

    hand_class, rank_value = evaluate_3(board.front)

    # Trips always qualify
    if hand_class == FRONT_THREE_KIND:
        return True

    # Pair of Q+ qualifies (Q=10, K=11, A=12)
    if hand_class == FRONT_ONE_PAIR:
        pair_rank = rank_value // 13
        return pair_rank >= 10  # Q, K, or A

    return False


def stays_fantasyland(board: OFCBoard) -> bool:
    """Check if a board qualifies to STAY in Fantasyland.

    Common rules (may vary by house):
    - Front: trips
    - Middle: full house or better
    - Back: quads or better
    """
    if not board.is_complete() or board.is_fouled():
        return False

    front_class, _ = evaluate_3(board.front)
    middle_class, _ = evaluate_5(board.middle)
    back_class, _ = evaluate_5(board.back)

    if front_class == FRONT_THREE_KIND:
        return True
    if middle_class <= HAND_FULL_HOUSE:  # Full house or better
        return True
    if back_class <= HAND_FOUR_KIND:  # Quads or better
        return True

    return False


# ---------------------------------------------------------------------------
# Estimated royalties for partial hands (used by solver heuristics)
# ---------------------------------------------------------------------------

def estimate_royalties(board: OFCBoard) -> float:
    """Estimate royalties for a partially-filled board.

    Used as a heuristic in the solver. Returns actual royalties for
    complete rows, and 0 for incomplete rows.
    """
    total = 0.0
    if board.is_front_full():
        total += royalties_front(board.front)
    if board.is_middle_full():
        total += royalties_middle(board.middle)
    if board.is_back_full():
        total += royalties_back(board.back)
    return total
