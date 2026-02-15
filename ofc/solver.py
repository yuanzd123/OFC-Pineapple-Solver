"""
Monte Carlo solver for OFC Pineapple.

Given a board state and cards to place, evaluates all possible placements
by running Monte Carlo simulations of random board completions.

For each candidate placement:
  1. Place the cards on the board
  2. Randomly complete the remaining slots from unknown cards
  3. Score the completed board (royalties + foul avoidance)
  4. Average the scores across N simulations
  5. Return the placement with the highest expected value

The solver works for both:
  - Initial deal (5 cards → place all 5)
  - Pineapple rounds (3 cards → place 2, discard 1)
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from itertools import combinations, permutations, product
from multiprocessing import Pool, cpu_count
from typing import Optional, Sequence

from ofc.board import GameState, OFCBoard, Row, ROW_CAPACITY
from ofc.card import (
    Deck,
    card_to_pretty,
    cards_to_pretty,
    cards_to_str,
)
from ofc.evaluator import evaluate_3_score, evaluate_5_score
from ofc.scoring import (
    estimate_royalties,
    qualifies_fantasyland,
    total_royalties,
)

# ---------------------------------------------------------------------------
# Solver result
# ---------------------------------------------------------------------------

@dataclass
class Placement:
    """A single card placement: which card goes to which row."""
    card: int
    row: Row

    def __repr__(self) -> str:
        return f"{card_to_pretty(self.card)} → {Row(self.row).name}"


@dataclass
class SolverResult:
    """Result of solver computation."""
    placements: list[Placement]       # Cards to place and where
    discard: Optional[int]            # Card to discard (None for initial deal)
    expected_value: float             # Expected score/royalty value
    simulations: int                  # Number of simulations run
    elapsed_seconds: float            # Time taken
    all_options: list[tuple[list[Placement], Optional[int], float]]  # All evaluated options

    def display(self) -> str:
        lines = []
        lines.append("═══ Solver Recommendation ═══")
        for p in self.placements:
            lines.append(f"  Place {card_to_pretty(p.card)} → {p.row.name}")
        if self.discard is not None:
            lines.append(f"  Discard {card_to_pretty(self.discard)}")
        lines.append(f"  Expected Value: {self.expected_value:.2f}")
        lines.append(f"  ({self.simulations} sims in {self.elapsed_seconds:.1f}s)")

        if len(self.all_options) > 1:
            lines.append("\n  All options (ranked):")
            for i, (placements, discard, ev) in enumerate(self.all_options[:8]):
                desc = ", ".join(f"{card_to_pretty(p.card)}→{p.row.name}" for p in placements)
                disc = f" disc {card_to_pretty(discard)}" if discard is not None else ""
                marker = " ◀ BEST" if i == 0 else ""
                lines.append(f"    {i+1}. [{desc}{disc}] EV={ev:.2f}{marker}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core solver
# ---------------------------------------------------------------------------

DEFAULT_SIMULATIONS = 3000
FANTASYLAND_BONUS = 8  # Extra EV points for qualifying for Fantasyland


def solve(
    state: GameState,
    num_simulations: int = DEFAULT_SIMULATIONS,
    parallel: bool = False,
) -> SolverResult:
    """Find the best placement for the current game state.

    Args:
        state: current game state with hand cards
        num_simulations: simulations per placement option
        parallel: use multiprocessing (recommended for large sim counts)

    Returns:
        SolverResult with best placements
    """
    start = time.time()

    if state.is_initial_deal:
        options = _generate_initial_placements(state)
    else:
        options = _generate_pineapple_placements(state)

    if not options:
        raise ValueError("No valid placements available")

    # Evaluate each option
    scored_options = []
    for placements, discard in options:
        ev = _evaluate_placement(state, placements, discard, num_simulations)
        scored_options.append((placements, discard, ev))

    # Sort by EV descending
    scored_options.sort(key=lambda x: x[2], reverse=True)

    best_placements, best_discard, best_ev = scored_options[0]

    elapsed = time.time() - start
    return SolverResult(
        placements=best_placements,
        discard=best_discard,
        expected_value=best_ev,
        simulations=num_simulations,
        elapsed_seconds=elapsed,
        all_options=scored_options,
    )


# ---------------------------------------------------------------------------
# Placement generation
# ---------------------------------------------------------------------------

def _generate_pineapple_placements(
    state: GameState,
) -> list[tuple[list[Placement], Optional[int]]]:
    """Generate all valid pineapple placements: pick 2 of 3 cards, discard 1."""
    hand = state.hand
    assert len(hand) == 3, f"Pineapple round requires 3 cards in hand, got {len(hand)}"

    options = []
    available_rows = [r for r in Row if state.board.can_place(r)]

    # Choose which card to discard (3 choices)
    for discard_idx in range(3):
        discard_card = hand[discard_idx]
        place_cards = [hand[i] for i in range(3) if i != discard_idx]

        # For the 2 cards to place, try all row combinations
        for row_combo in product(available_rows, repeat=2):
            # Check that we don't overfill any row
            board_copy = state.board.copy()
            valid = True
            placements = []
            for card, row in zip(place_cards, row_combo):
                if board_copy.can_place(row):
                    board_copy.place_card(row, card)
                    placements.append(Placement(card=card, row=row))
                else:
                    valid = False
                    break

            if valid and len(placements) == 2:
                options.append((placements, discard_card))

    # Deduplicate (same cards in same rows, different order)
    seen = set()
    unique_options = []
    for placements, discard in options:
        key = tuple(sorted((p.card, p.row) for p in placements)) + (discard,)
        if key not in seen:
            seen.add(key)
            unique_options.append((placements, discard))

    return unique_options


def _generate_initial_placements(
    state: GameState,
) -> list[tuple[list[Placement], Optional[int]]]:
    """Generate placements for the initial 5 cards.

    This has a large combinatorial space, so we use heuristics to prune.
    With 5 cards and 3 rows, there are up to 3^5 = 243 raw combos,
    but many are invalid (overfilling rows).
    """
    hand = state.hand
    assert len(hand) == 5, f"Initial deal requires 5 cards in hand, got {len(hand)}"

    options = []
    rows = list(Row)

    # Generate all valid distributions of 5 cards into 3 rows
    for row_assignment in product(rows, repeat=5):
        # Check capacity constraints
        row_counts = {Row.FRONT: 0, Row.MIDDLE: 0, Row.BACK: 0}
        for r in row_assignment:
            row_counts[r] += 1
            if row_counts[r] > ROW_CAPACITY[r]:
                break
        else:
            placements = [Placement(card=c, row=r) for c, r in zip(hand, row_assignment)]
            options.append((placements, None))

    # Deduplicate
    seen = set()
    unique_options = []
    for placements, discard in options:
        key = tuple(sorted((p.card, p.row) for p in placements))
        if key not in seen:
            seen.add(key)
            unique_options.append((placements, discard))

    return unique_options


# ---------------------------------------------------------------------------
# Monte Carlo evaluation
# ---------------------------------------------------------------------------

def _evaluate_placement(
    state: GameState,
    placements: list[Placement],
    discard: Optional[int],
    num_simulations: int,
) -> float:
    """Evaluate a placement by Monte Carlo simulation.

    Simulates completing the board randomly and averages the resulting scores.
    """
    # Apply the placement to a copy of the board
    board = state.board.copy()
    for p in placements:
        board.place_card(p.row, p.card)

    # If board is already complete, just score it
    if board.is_complete():
        return _score_board(board)

    # Determine remaining cards in the deck
    known = state.all_known_cards()
    # Add placed cards to known
    for p in placements:
        known.add(p.card)
    if discard is not None:
        known.add(discard)

    remaining_deck = [c for c in range(52) if c not in known]
    slots_needed = 13 - board.total_cards()

    if slots_needed == 0:
        return _score_board(board)

    # Run simulations
    total_score = 0.0
    actual_sims = min(num_simulations, _max_combinations(len(remaining_deck), slots_needed))

    for _ in range(actual_sims):
        sim_board = board.copy()
        # Draw random cards to fill remaining slots
        fill_cards = random.sample(remaining_deck, slots_needed)
        _fill_board_greedy(sim_board, fill_cards)
        total_score += _score_board(sim_board)

    return total_score / actual_sims if actual_sims > 0 else 0.0


def _score_board(board: OFCBoard) -> float:
    """Score a complete board. Returns a numeric value (higher = better)."""
    if not board.is_complete():
        return estimate_royalties(board)

    if board.is_fouled():
        return -10.0  # Heavy penalty for fouling

    score = float(total_royalties(board))

    # Bonus for Fantasyland qualification
    if qualifies_fantasyland(board):
        score += FANTASYLAND_BONUS

    return score


def _fill_board_greedy(board: OFCBoard, cards: list[int]) -> None:
    """Fill remaining board slots with cards using a greedy approach.

    Fills back first, then middle, then front — since bottom rows
    need higher-value hands and we want to avoid fouling.
    """
    idx = 0
    for row in [Row.BACK, Row.MIDDLE, Row.FRONT]:
        while board.can_place(row) and idx < len(cards):
            board.place_card(row, cards[idx])
            idx += 1


def _max_combinations(n: int, k: int) -> int:
    """Calculate C(n,k) with a cap to avoid overflow."""
    if k > n:
        return 0
    if k == 0 or k == n:
        return 1
    k = min(k, n - k)
    result = 1
    for i in range(k):
        result = result * (n - i) // (i + 1)
        if result > 1_000_000:
            return 1_000_000
    return result
