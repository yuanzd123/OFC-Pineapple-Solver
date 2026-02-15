"""Tests for hand evaluator."""

import pytest

from ofc.card import cards_from_str
from ofc.evaluator import (
    HAND_FLUSH,
    HAND_FOUR_KIND,
    HAND_FULL_HOUSE,
    HAND_HIGH_CARD,
    HAND_ONE_PAIR,
    HAND_ROYAL_FLUSH,
    HAND_STRAIGHT,
    HAND_STRAIGHT_FLUSH,
    HAND_THREE_KIND,
    HAND_TWO_PAIR,
    FRONT_HIGH_CARD,
    FRONT_ONE_PAIR,
    FRONT_THREE_KIND,
    compare_3,
    compare_5,
    evaluate_3,
    evaluate_5,
    evaluate_5_score,
    hand_class_name_5,
)


class TestHandClassification:
    """Test that each hand type is classified correctly."""

    def test_royal_flush(self):
        cards = cards_from_str("Ah Kh Qh Jh Th")
        hand_class, _ = evaluate_5(cards)
        assert hand_class == HAND_ROYAL_FLUSH

    def test_straight_flush(self):
        cards = cards_from_str("9h 8h 7h 6h 5h")
        hand_class, _ = evaluate_5(cards)
        assert hand_class == HAND_STRAIGHT_FLUSH

    def test_four_of_a_kind(self):
        cards = cards_from_str("Ah Ac Ad As 2c")
        hand_class, _ = evaluate_5(cards)
        assert hand_class == HAND_FOUR_KIND

    def test_full_house(self):
        cards = cards_from_str("Ah Ac Ad Ks Kc")
        hand_class, _ = evaluate_5(cards)
        assert hand_class == HAND_FULL_HOUSE

    def test_flush(self):
        cards = cards_from_str("Ah Th 8h 5h 3h")
        hand_class, _ = evaluate_5(cards)
        assert hand_class == HAND_FLUSH

    def test_straight(self):
        cards = cards_from_str("Ts 9c 8h 7d 6s")
        hand_class, _ = evaluate_5(cards)
        assert hand_class == HAND_STRAIGHT

    def test_wheel_straight(self):
        """A-2-3-4-5 should be a straight."""
        cards = cards_from_str("Ah 2c 3d 4s 5h")
        hand_class, _ = evaluate_5(cards)
        assert hand_class == HAND_STRAIGHT

    def test_three_of_a_kind(self):
        cards = cards_from_str("Ah Ac Ad Ks 3c")
        hand_class, _ = evaluate_5(cards)
        assert hand_class == HAND_THREE_KIND

    def test_two_pair(self):
        cards = cards_from_str("Ah Ac Kd Ks 3c")
        hand_class, _ = evaluate_5(cards)
        assert hand_class == HAND_TWO_PAIR

    def test_one_pair(self):
        cards = cards_from_str("Ah Ac Kd Qs 3c")
        hand_class, _ = evaluate_5(cards)
        assert hand_class == HAND_ONE_PAIR

    def test_high_card(self):
        cards = cards_from_str("Ah Tc 8d 5s 3c")
        hand_class, _ = evaluate_5(cards)
        assert hand_class == HAND_HIGH_CARD


class TestHandRanking:
    """Test that hands are ranked correctly relative to each other."""

    def test_royal_beats_straight_flush(self):
        royal = cards_from_str("Ah Kh Qh Jh Th")
        sf = cards_from_str("9h 8h 7h 6h 5h")
        assert compare_5(royal, sf) > 0

    def test_quads_beat_full_house(self):
        quads = cards_from_str("Ah Ac Ad As 2c")
        fh = cards_from_str("Kh Kc Kd Qs Qc")
        assert compare_5(quads, fh) > 0

    def test_flush_beats_straight(self):
        flush = cards_from_str("Ah Th 8h 5h 3h")
        straight = cards_from_str("Ts 9c 8h 7d 6s")
        assert compare_5(flush, straight) > 0

    def test_higher_pair_beats_lower(self):
        aa = cards_from_str("Ah Ac Kd Qs 3c")
        kk = cards_from_str("Kh Kc Qd Js 3c")
        assert compare_5(aa, kk) > 0

    def test_higher_kicker(self):
        aak = cards_from_str("Ah Ac Kd 5s 3c")
        aaq = cards_from_str("Ah Ac Qd 5s 3c")
        # Both are pair of aces, but different kicker
        # Since they share cards, let's use different suits
        aak = cards_from_str("Ah As Kd 5c 3d")
        aaq = cards_from_str("Ah As Qd 5c 3d")
        assert compare_5(aak, aaq) > 0

    def test_wheel_loses_to_six_high(self):
        wheel = cards_from_str("Ah 2c 3d 4s 5h")
        six_high = cards_from_str("6h 5c 4d 3s 2h")
        assert compare_5(six_high, wheel) > 0

    def test_same_hand_ties(self):
        h1 = cards_from_str("Ah Kh Qh Jh Th")
        h2 = cards_from_str("As Ks Qs Js Ts")
        assert compare_5(h1, h2) == 0

    def test_class_hierarchy(self):
        """Verify the complete hierarchy: RF > SF > 4K > FH > F > S > 3K > 2P > P > HC."""
        hands = [
            cards_from_str("Ah Kh Qh Jh Th"),  # Royal Flush
            cards_from_str("9h 8h 7h 6h 5h"),  # Straight Flush
            cards_from_str("Ac Ad As Ah 2c"),   # Four of a Kind (Aces)
            cards_from_str("Kc Kd Ks Qh Qc"),  # Full House
            cards_from_str("Ah Th 8h 5h 3h"),   # Flush
            cards_from_str("Ts 9c 8h 7d 6s"),   # Straight
            cards_from_str("Jc Jd Js 8h 3c"),   # Three of a Kind
            cards_from_str("Tc Td 9h 9s 3c"),   # Two Pair
            cards_from_str("8c 8d Ah Ks 3c"),   # One Pair
            cards_from_str("Ac Tc 8d 5s 3h"),   # High Card
        ]
        for i in range(len(hands) - 1):
            result = compare_5(hands[i], hands[i + 1])
            assert result > 0, (
                f"Expected {hand_class_name_5(hands[i])} > "
                f"{hand_class_name_5(hands[i + 1])}, got {result}"
            )


class TestFrontRow:
    """Test 3-card front row evaluation."""

    def test_trips(self):
        cards = cards_from_str("Ah Ac Ad")
        hand_class, _ = evaluate_3(cards)
        assert hand_class == FRONT_THREE_KIND

    def test_pair(self):
        cards = cards_from_str("Ah Ac Kd")
        hand_class, _ = evaluate_3(cards)
        assert hand_class == FRONT_ONE_PAIR

    def test_high_card(self):
        cards = cards_from_str("Ah Kc Qd")
        hand_class, _ = evaluate_3(cards)
        assert hand_class == FRONT_HIGH_CARD

    def test_trips_beat_pair(self):
        trips = cards_from_str("2c 2d 2h")
        pair = cards_from_str("Ah Ac Kd")
        assert compare_3(trips, pair) > 0

    def test_pair_beats_high_card(self):
        pair = cards_from_str("2c 2d Ah")
        hc = cards_from_str("Ah Kc Qd")
        assert compare_3(pair, hc) > 0

    def test_higher_pair_wins(self):
        aa = cards_from_str("Ah Ac 2d")
        kk = cards_from_str("Kh Kc Qd")
        assert compare_3(aa, kk) > 0
