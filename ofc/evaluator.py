"""
Poker hand evaluator for OFC Pineapple.

Evaluates both 5-card hands (middle/back rows) and 3-card hands (front row).
Returns integer rankings where LOWER = BETTER (like golf scoring).

5-card hand classes (best to worst):
    1 = Royal Flush
    2 = Straight Flush
    3 = Four of a Kind
    4 = Full House
    5 = Flush
    6 = Straight
    7 = Three of a Kind
    8 = Two Pair
    9 = One Pair
   10 = High Card

3-card hand classes (front row only):
    1 = Three of a Kind (trips)
    2 = One Pair
    3 = High Card
"""

from __future__ import annotations

from collections import Counter
from typing import Sequence

from ofc.card import card_rank, card_suit

# ---------------------------------------------------------------------------
# Hand class constants (lower = better)
# ---------------------------------------------------------------------------

HAND_ROYAL_FLUSH = 1
HAND_STRAIGHT_FLUSH = 2
HAND_FOUR_KIND = 3
HAND_FULL_HOUSE = 4
HAND_FLUSH = 5
HAND_STRAIGHT = 6
HAND_THREE_KIND = 7
HAND_TWO_PAIR = 8
HAND_ONE_PAIR = 9
HAND_HIGH_CARD = 10

HAND_CLASS_NAMES = {
    HAND_ROYAL_FLUSH: "Royal Flush",
    HAND_STRAIGHT_FLUSH: "Straight Flush",
    HAND_FOUR_KIND: "Four of a Kind",
    HAND_FULL_HOUSE: "Full House",
    HAND_FLUSH: "Flush",
    HAND_STRAIGHT: "Straight",
    HAND_THREE_KIND: "Three of a Kind",
    HAND_TWO_PAIR: "Two Pair",
    HAND_ONE_PAIR: "One Pair",
    HAND_HIGH_CARD: "High Card",
}

FRONT_THREE_KIND = 1
FRONT_ONE_PAIR = 2
FRONT_HIGH_CARD = 3

FRONT_CLASS_NAMES = {
    FRONT_THREE_KIND: "Three of a Kind",
    FRONT_ONE_PAIR: "One Pair",
    FRONT_HIGH_CARD: "High Card",
}


# ---------------------------------------------------------------------------
# 5-card evaluator
# ---------------------------------------------------------------------------

def evaluate_5(cards: Sequence[int]) -> tuple[int, int]:
    """Evaluate a 5-card poker hand.

    Returns (hand_class, rank_value) where:
      - hand_class: 1-10, lower is better
      - rank_value: tie-breaking value within the class, higher is better

    The combined score for comparison: hand_class * 10_000_000 - rank_value
    Lower overall score = better hand.
    """
    assert len(cards) == 5, f"Expected 5 cards, got {len(cards)}"

    ranks = sorted([card_rank(c) for c in cards], reverse=True)
    suits = [card_suit(c) for c in cards]

    is_flush = len(set(suits)) == 1

    # Check for straight (including A-2-3-4-5 wheel)
    is_straight = False
    straight_high = 0
    unique_ranks = sorted(set(ranks), reverse=True)
    if len(unique_ranks) == 5:
        if unique_ranks[0] - unique_ranks[4] == 4:
            is_straight = True
            straight_high = unique_ranks[0]
        # Wheel: A-2-3-4-5
        elif unique_ranks == [12, 3, 2, 1, 0]:
            is_straight = True
            straight_high = 3  # 5-high straight

    rank_counts = Counter(ranks)
    counts = sorted(rank_counts.values(), reverse=True)

    if is_straight and is_flush:
        if straight_high == 12:  # A-high straight flush = Royal Flush
            return (HAND_ROYAL_FLUSH, _rank_key(ranks))
        return (HAND_STRAIGHT_FLUSH, straight_high)

    if counts == [4, 1]:
        # Four of a kind: quad rank, then kicker
        quad_rank = _rank_with_count(rank_counts, 4)
        kicker = _rank_with_count(rank_counts, 1)
        return (HAND_FOUR_KIND, quad_rank * 13 + kicker)

    if counts == [3, 2]:
        # Full house: triple rank, then pair rank
        triple_rank = _rank_with_count(rank_counts, 3)
        pair_rank = _rank_with_count(rank_counts, 2)
        return (HAND_FULL_HOUSE, triple_rank * 13 + pair_rank)

    if is_flush:
        return (HAND_FLUSH, _rank_key(ranks))

    if is_straight:
        return (HAND_STRAIGHT, straight_high)

    if counts == [3, 1, 1]:
        triple_rank = _rank_with_count(rank_counts, 3)
        kickers = sorted(_ranks_with_count(rank_counts, 1), reverse=True)
        return (HAND_THREE_KIND, triple_rank * 169 + kickers[0] * 13 + kickers[1])

    if counts == [2, 2, 1]:
        pairs = sorted(_ranks_with_count(rank_counts, 2), reverse=True)
        kicker = _rank_with_count(rank_counts, 1)
        return (HAND_TWO_PAIR, pairs[0] * 169 + pairs[1] * 13 + kicker)

    if counts == [2, 1, 1, 1]:
        pair_rank = _rank_with_count(rank_counts, 2)
        kickers = sorted(_ranks_with_count(rank_counts, 1), reverse=True)
        return (HAND_ONE_PAIR, pair_rank * 2197 + kickers[0] * 169 + kickers[1] * 13 + kickers[2])

    return (HAND_HIGH_CARD, _rank_key(ranks))


def evaluate_5_score(cards: Sequence[int]) -> int:
    """Return a single integer score for a 5-card hand. Lower = better."""
    hand_class, rank_value = evaluate_5(cards)
    return hand_class * 100_000_000 - rank_value


# ---------------------------------------------------------------------------
# 3-card evaluator (front row)
# ---------------------------------------------------------------------------

def evaluate_3(cards: Sequence[int]) -> tuple[int, int]:
    """Evaluate a 3-card front-row hand.

    Front row only uses: trips > pair > high card.
    Straights and flushes don't count for the front row.

    Returns (hand_class, rank_value).
    """
    assert len(cards) == 3, f"Expected 3 cards, got {len(cards)}"

    ranks = sorted([card_rank(c) for c in cards], reverse=True)
    rank_counts = Counter(ranks)
    counts = sorted(rank_counts.values(), reverse=True)

    if counts == [3]:
        trip_rank = ranks[0]
        return (FRONT_THREE_KIND, trip_rank)

    if counts == [2, 1]:
        pair_rank = _rank_with_count(rank_counts, 2)
        kicker = _rank_with_count(rank_counts, 1)
        return (FRONT_ONE_PAIR, pair_rank * 13 + kicker)

    # High card
    return (FRONT_HIGH_CARD, ranks[0] * 169 + ranks[1] * 13 + ranks[2])


def evaluate_3_score(cards: Sequence[int]) -> int:
    """Return a single integer score for a 3-card hand. Lower = better."""
    hand_class, rank_value = evaluate_3(cards)
    return hand_class * 100_000 - rank_value


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------

def hand_class_name_5(cards: Sequence[int]) -> str:
    """Return the name of the hand class for a 5-card hand."""
    hand_class, _ = evaluate_5(cards)
    return HAND_CLASS_NAMES[hand_class]


def hand_class_name_3(cards: Sequence[int]) -> str:
    """Return the name of the hand class for a 3-card hand."""
    hand_class, _ = evaluate_3(cards)
    return FRONT_CLASS_NAMES[hand_class]


def compare_5(hand_a: Sequence[int], hand_b: Sequence[int]) -> int:
    """Compare two 5-card hands. Returns >0 if a wins, <0 if b wins, 0 if tie."""
    score_a = evaluate_5_score(hand_a)
    score_b = evaluate_5_score(hand_b)
    # Lower score = better, so if a < b, a wins => return positive
    if score_a < score_b:
        return 1
    elif score_a > score_b:
        return -1
    return 0


def compare_3(hand_a: Sequence[int], hand_b: Sequence[int]) -> int:
    """Compare two 3-card hands. Returns >0 if a wins, <0 if b wins, 0 if tie."""
    score_a = evaluate_3_score(hand_a)
    score_b = evaluate_3_score(hand_b)
    if score_a < score_b:
        return 1
    elif score_a > score_b:
        return -1
    return 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _rank_key(sorted_ranks: list[int]) -> int:
    """Convert a sorted-descending rank list into a single comparable int."""
    result = 0
    for r in sorted_ranks:
        result = result * 13 + r
    return result


def _rank_with_count(counts: Counter, n: int) -> int:
    """Return the rank that appears exactly n times."""
    for rank, count in counts.items():
        if count == n:
            return rank
    raise ValueError(f"No rank with count {n}")


def _ranks_with_count(counts: Counter, n: int) -> list[int]:
    """Return all ranks that appear exactly n times."""
    return [rank for rank, count in counts.items() if count == n]
