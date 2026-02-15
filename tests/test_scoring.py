"""Tests for scoring module."""

import pytest

from ofc.board import OFCBoard, Row
from ofc.card import cards_from_str
from ofc.scoring import (
    qualifies_fantasyland,
    royalties_back,
    royalties_front,
    royalties_middle,
    score_head_to_head,
    total_royalties,
)


class TestBackRoyalties:
    def test_straight(self):
        cards = cards_from_str("Ts 9c 8h 7d 6s")
        assert royalties_back(cards) == 2

    def test_flush(self):
        cards = cards_from_str("Ah Th 8h 5h 3h")
        assert royalties_back(cards) == 4

    def test_full_house(self):
        cards = cards_from_str("Ah Ac Ad Ks Kc")
        assert royalties_back(cards) == 6

    def test_four_of_a_kind(self):
        cards = cards_from_str("Ah Ac Ad As 2c")
        assert royalties_back(cards) == 10

    def test_straight_flush(self):
        cards = cards_from_str("9h 8h 7h 6h 5h")
        assert royalties_back(cards) == 15

    def test_royal_flush(self):
        cards = cards_from_str("Ah Kh Qh Jh Th")
        assert royalties_back(cards) == 25

    def test_no_royalty_pair(self):
        cards = cards_from_str("Ah Ac Kd Qs 3c")
        assert royalties_back(cards) == 0

    def test_no_royalty_high_card(self):
        cards = cards_from_str("Ah Tc 8d 5s 3c")
        assert royalties_back(cards) == 0


class TestMiddleRoyalties:
    def test_three_of_a_kind(self):
        cards = cards_from_str("Ah Ac Ad 5s 3c")
        assert royalties_middle(cards) == 2

    def test_straight(self):
        cards = cards_from_str("Ts 9c 8h 7d 6s")
        assert royalties_middle(cards) == 4

    def test_flush(self):
        cards = cards_from_str("Ah Th 8h 5h 3h")
        assert royalties_middle(cards) == 8

    def test_full_house(self):
        cards = cards_from_str("Ah Ac Ad Ks Kc")
        assert royalties_middle(cards) == 12

    def test_four_of_a_kind(self):
        cards = cards_from_str("Ah Ac Ad As 2c")
        assert royalties_middle(cards) == 20

    def test_royal_flush(self):
        cards = cards_from_str("Ah Kh Qh Jh Th")
        assert royalties_middle(cards) == 50


class TestFrontRoyalties:
    def test_pair_of_sixes(self):
        cards = cards_from_str("6h 6c 2d")
        assert royalties_front(cards) == 1

    def test_pair_of_aces(self):
        cards = cards_from_str("Ah Ac 2d")
        assert royalties_front(cards) == 9

    def test_pair_of_fives_no_royalty(self):
        cards = cards_from_str("5h 5c 2d")
        assert royalties_front(cards) == 0

    def test_trips_of_twos(self):
        cards = cards_from_str("2h 2c 2d")
        assert royalties_front(cards) == 10

    def test_trips_of_aces(self):
        cards = cards_from_str("Ah Ac Ad")
        assert royalties_front(cards) == 22

    def test_high_card_no_royalty(self):
        cards = cards_from_str("Ah Kc Qd")
        assert royalties_front(cards) == 0


class TestTotalRoyalties:
    def test_complete_board_with_royalties(self):
        board = OFCBoard()
        # Front: pair of Aces (+9)
        for c in cards_from_str("Ah Ac 2d"):
            board.place_card(Row.FRONT, c)
        # Middle: flush (+8)
        for c in cards_from_str("Kh Th 8h 5h 3h"):
            board.place_card(Row.MIDDLE, c)
        # Back: full house (+6)
        for c in cards_from_str("Qs Qc Qd 9s 9c"):
            board.place_card(Row.BACK, c)

        # This board is NOT fouled (back=FH >= mid=flush >= front=pair)
        # Wait: FH > flush, so back >= middle ✓
        # But we need to check middle >= front: flush vs pair — flush is better ✓
        # Actually in OFC the comparison is back >= middle (both 5-card), and
        # the front 3-card is always weaker. So this should be valid.
        assert not board.is_fouled()
        assert total_royalties(board) == 9 + 8 + 6  # 23

    def test_fouled_board_no_royalties(self):
        board = OFCBoard()
        # Front: pair of Aces
        for c in cards_from_str("Ah Ac 2d"):
            board.place_card(Row.FRONT, c)
        # Middle: full house (strong)
        for c in cards_from_str("Ks Kc Kd Qs Qc"):
            board.place_card(Row.MIDDLE, c)
        # Back: pair (weak — weaker than middle = FOUL)
        for c in cards_from_str("3h 3c 9d 7s 5c"):
            board.place_card(Row.BACK, c)

        assert board.is_fouled()
        assert total_royalties(board) == 0


class TestFantasyland:
    def test_qq_front_qualifies(self):
        board = OFCBoard()
        for c in cards_from_str("Qh Qc 2d"):
            board.place_card(Row.FRONT, c)
        for c in cards_from_str("Ts 9c 8h 7d 6s"):
            board.place_card(Row.MIDDLE, c)
        for c in cards_from_str("Ah Kh Jh Th 5h"):
            board.place_card(Row.BACK, c)
        # Back=flush >= Mid=straight -> not fouled
        assert not board.is_fouled()
        assert qualifies_fantasyland(board)

    def test_jj_front_does_not_qualify(self):
        board = OFCBoard()
        for c in cards_from_str("Jh Jc 2d"):
            board.place_card(Row.FRONT, c)
        for c in cards_from_str("Ts 9c 8h 7d 6s"):
            board.place_card(Row.MIDDLE, c)
        for c in cards_from_str("Ah Kh Qh 4h 3h"):
            board.place_card(Row.BACK, c)
        assert not board.is_fouled()
        assert not qualifies_fantasyland(board)


class TestHeadToHead:
    def test_both_fouled_zero(self):
        board1 = OFCBoard()
        board2 = OFCBoard()
        # Create two fouled boards
        for c in cards_from_str("Ah Ac 2d"):
            board1.place_card(Row.FRONT, c)
        for c in cards_from_str("Ks Kc Kd Qs Qc"):
            board1.place_card(Row.MIDDLE, c)
        for c in cards_from_str("3h 3c 9d 7s 5c"):
            board1.place_card(Row.BACK, c)

        for c in cards_from_str("Jh Jd 4d"):
            board2.place_card(Row.FRONT, c)
        for c in cards_from_str("Ts Td Tc 8s 8c"):
            board2.place_card(Row.MIDDLE, c)
        for c in cards_from_str("2h 2s 6d 4s 4c"):
            board2.place_card(Row.BACK, c)

        assert board1.is_fouled()
        assert board2.is_fouled()
        assert score_head_to_head(board1, board2) == 0
