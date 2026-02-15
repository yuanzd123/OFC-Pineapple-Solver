"""Tests for card module."""

from ofc.card import (
    Deck,
    card_from_str,
    card_rank,
    card_suit,
    card_to_pretty,
    card_to_str,
    cards_from_str,
    cards_to_pretty,
    cards_to_str,
)

import pytest


class TestCardParsing:
    def test_ace_of_hearts(self):
        c = card_from_str("Ah")
        assert card_rank(c) == 12  # Ace = 12
        assert card_suit(c) == 2   # Hearts = 2

    def test_two_of_clubs(self):
        c = card_from_str("2c")
        assert card_rank(c) == 0
        assert card_suit(c) == 0

    def test_ten_of_spades(self):
        c = card_from_str("Ts")
        assert card_rank(c) == 8  # Ten = 8
        assert card_suit(c) == 3  # Spades = 3

    def test_roundtrip(self):
        for s in ["Ah", "2c", "Ts", "Kd", "Qh", "Jc", "9s", "5d"]:
            assert card_to_str(card_from_str(s)) == s

    def test_invalid_rank(self):
        with pytest.raises(ValueError):
            card_from_str("Xh")

    def test_invalid_suit(self):
        with pytest.raises(ValueError):
            card_from_str("Ax")

    def test_invalid_length(self):
        with pytest.raises(ValueError):
            card_from_str("A")

    def test_case_insensitive_suit(self):
        assert card_from_str("AH") == card_from_str("Ah")
        assert card_from_str("tS") == card_from_str("Ts")


class TestCardsFromStr:
    def test_parse_multiple(self):
        cards = cards_from_str("Ah Kh Qh Jh Th")
        assert len(cards) == 5

    def test_comma_separated(self):
        cards = cards_from_str("Ah,Kh,Qh")
        assert len(cards) == 3

    def test_to_str_roundtrip(self):
        s = "Ah Kh Qh Jh Th"
        assert cards_to_str(cards_from_str(s)) == s


class TestCardPretty:
    def test_pretty_ace_hearts(self):
        c = card_from_str("Ah")
        assert card_to_pretty(c) == "A♥"

    def test_pretty_multiple(self):
        cards = cards_from_str("Ah Kc 2d")
        result = cards_to_pretty(cards)
        assert "A♥" in result
        assert "K♣" in result
        assert "2♦" in result


class TestDeck:
    def test_full_deck(self):
        d = Deck()
        assert d.size == 52

    def test_deal(self):
        d = Deck()
        cards = d.deal(5)
        assert len(cards) == 5
        assert d.size == 47

    def test_remove(self):
        d = Deck()
        ah = card_from_str("Ah")
        d.remove(ah)
        assert d.size == 51
        assert ah not in d

    def test_remove_str(self):
        d = Deck()
        d.remove_str("Ah Kh")
        assert d.size == 50

    def test_deal_too_many(self):
        d = Deck()
        with pytest.raises(ValueError):
            d.deal(53)

    def test_copy(self):
        d = Deck()
        d.deal(5)
        d2 = d.copy()
        assert d.size == d2.size
        d2.deal(5)
        assert d.size == 47
        assert d2.size == 42

    def test_unique_cards(self):
        d = Deck()
        all_cards = d.deal(52)
        assert len(set(all_cards)) == 52
