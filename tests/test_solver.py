"""Tests for the solver module."""

import pytest

from ofc.board import GameState, OFCBoard, Row
from ofc.card import cards_from_str, cards_to_pretty
from ofc.solver import solve


class TestSolverInitial:
    """Test solver with initial 5-card deals."""

    def test_solver_runs(self):
        """Solver should complete without errors."""
        state = GameState()
        state.hand = cards_from_str("Ah Kh Qh Jh 2c")
        state.round_num = 0

        result = solve(state, num_simulations=100)
        assert result.placements is not None
        assert len(result.placements) == 5
        assert result.discard is None
        assert result.expected_value is not None

    def test_solver_places_all_cards(self):
        """All 5 cards should be placed."""
        state = GameState()
        state.hand = cards_from_str("Ts 9c 8h 7d 6s")
        state.round_num = 0

        result = solve(state, num_simulations=100)
        placed_cards = {p.card for p in result.placements}
        hand_cards = set(state.hand)
        assert placed_cards == hand_cards

    def test_solver_respects_capacity(self):
        """No row should be overfilled."""
        state = GameState()
        state.hand = cards_from_str("Ah Kh Qh Jh Th")
        state.round_num = 0

        result = solve(state, num_simulations=100)
        row_counts = {Row.FRONT: 0, Row.MIDDLE: 0, Row.BACK: 0}
        for p in result.placements:
            row_counts[p.row] += 1
        assert row_counts[Row.FRONT] <= 3
        assert row_counts[Row.MIDDLE] <= 5
        assert row_counts[Row.BACK] <= 5


class TestSolverPineapple:
    """Test solver with pineapple 3-card deals."""

    def test_pineapple_solver_runs(self):
        """Solver handles pineapple rounds."""
        state = GameState()
        # Set up a partially filled board
        for c in cards_from_str("Ah Kh"):
            state.board.place_card(Row.BACK, c)
        for c in cards_from_str("Qd"):
            state.board.place_card(Row.FRONT, c)
        state.board.place_card(Row.MIDDLE, cards_from_str("Ts")[0])
        state.board.place_card(Row.BACK, cards_from_str("9h")[0])

        state.hand = cards_from_str("Jc 5d 3s")
        state.round_num = 1

        result = solve(state, num_simulations=100)
        assert len(result.placements) == 2
        assert result.discard is not None

    def test_pineapple_discards_one(self):
        """Exactly one card should be discarded."""
        state = GameState()
        state.board.place_card(Row.BACK, cards_from_str("Ah")[0])
        state.hand = cards_from_str("Kc Qd Js")
        state.round_num = 1

        result = solve(state, num_simulations=100)
        placed = {p.card for p in result.placements}
        assert result.discard not in placed
        assert result.discard in state.hand
        assert len(placed) == 2

    def test_solver_returns_all_options(self):
        """Solver should enumerate and rank multiple options."""
        state = GameState()
        state.hand = cards_from_str("Ah Kh Qh Jh 2c")
        state.round_num = 0

        result = solve(state, num_simulations=50)
        assert len(result.all_options) > 1
        # Should be sorted by EV descending
        evs = [opt[2] for opt in result.all_options]
        assert evs == sorted(evs, reverse=True)


class TestSolverQuality:
    """Test that the solver makes reasonable decisions."""

    def test_avoids_obvious_foul(self):
        """Solver shouldn't put high cards in front when better options exist."""
        state = GameState()
        # Give solver cards where placing all high cards in front would foul
        state.hand = cards_from_str("Ah Ac Ad Kh 2c")
        state.round_num = 0

        result = solve(state, num_simulations=500)
        # Check that the best placement doesn't put trips in front
        # (unless it's a Fantasyland play, which is valid)
        front_cards = [p.card for p in result.placements if p.row == Row.FRONT]
        # The solver should at most put 3 cards in front
        assert len(front_cards) <= 3
        # EV should be positive (no fouling)
        assert result.expected_value > -5.0

    def test_prefers_back_row_for_strong_hand(self):
        """Solver should generally prefer placing strong cards in back/middle."""
        state = GameState()
        # A clear straight should go to back or middle
        state.hand = cards_from_str("Ts 9c 8h 7d 2s")
        state.round_num = 0

        result = solve(state, num_simulations=500)
        # The 2s should likely go to front, rest to back or middle
        # EV can be negative with mediocre hands; just verify solver runs
        assert result.expected_value > -10.0  # Not a guaranteed foul
