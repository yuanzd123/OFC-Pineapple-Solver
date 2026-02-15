"""
OFC Board representation.

An OFC board has three rows:
  - front:  3 cards (ranked as 3-card poker hand)
  - middle: 5 cards (ranked as 5-card poker hand)
  - back:   5 cards (ranked as 5-card poker hand)

The board is valid (not fouled) when: back >= middle >= front.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional, Sequence

from ofc.card import card_to_pretty, cards_to_pretty, cards_to_str
from ofc.evaluator import compare_middle_front, evaluate_3_score, evaluate_5_score


class Row(IntEnum):
    """Board row identifiers."""
    FRONT = 0
    MIDDLE = 1
    BACK = 2


ROW_NAMES = {Row.FRONT: "Front", Row.MIDDLE: "Middle", Row.BACK: "Back"}
ROW_CAPACITY = {Row.FRONT: 3, Row.MIDDLE: 5, Row.BACK: 5}


@dataclass
class OFCBoard:
    """Represents a single player's OFC board state."""

    front: list[int] = field(default_factory=list)
    middle: list[int] = field(default_factory=list)
    back: list[int] = field(default_factory=list)

    def row(self, r: Row) -> list[int]:
        """Get the cards in a specific row."""
        if r == Row.FRONT:
            return self.front
        elif r == Row.MIDDLE:
            return self.middle
        else:
            return self.back

    def row_remaining(self, r: Row) -> int:
        """Number of empty slots in a row."""
        return ROW_CAPACITY[r] - len(self.row(r))

    def can_place(self, r: Row) -> bool:
        """Check if a card can be placed in the given row."""
        return self.row_remaining(r) > 0

    def place_card(self, r: Row, card: int) -> None:
        """Place a card in the given row. Raises if row is full."""
        row_cards = self.row(r)
        if len(row_cards) >= ROW_CAPACITY[r]:
            raise ValueError(f"{ROW_NAMES[r]} row is full ({ROW_CAPACITY[r]} cards)")
        row_cards.append(card)

    def total_cards(self) -> int:
        """Total number of cards placed on the board."""
        return len(self.front) + len(self.middle) + len(self.back)

    def is_complete(self) -> bool:
        """Board is complete when all 13 slots are filled."""
        return self.total_cards() == 13

    def is_front_full(self) -> bool:
        return len(self.front) == 3

    def is_middle_full(self) -> bool:
        return len(self.middle) == 5

    def is_back_full(self) -> bool:
        return len(self.back) == 5

    def is_fouled(self) -> bool:
        """Check if the board is fouled (invalid hand ordering).

        A board is fouled if back < middle or middle < front.
        Can only be checked when all rows are full.
        """
        if not self.is_complete():
            return False

        # Check back >= middle (both 5-card, lower score = better)
        back_score = evaluate_5_score(self.back)
        middle_score = evaluate_5_score(self.middle)
        if back_score > middle_score:
            return True  # back is weaker than middle = foul

        # Check middle >= front (5-card vs 3-card cross-row comparison)
        if compare_middle_front(self.middle, self.front) < 0:
            return True  # front is stronger than middle = foul

        return False

    def all_cards(self) -> list[int]:
        """Return all cards currently on the board."""
        return self.front + self.middle + self.back

    def copy(self) -> "OFCBoard":
        """Create a deep copy of this board."""
        return OFCBoard(
            front=list(self.front),
            middle=list(self.middle),
            back=list(self.back),
        )

    def display(self) -> str:
        """Pretty-print the board state."""
        lines = []
        lines.append("┌─────────────────────────┐")
        lines.append(f"│ Front  ({len(self.front)}/3): {_pad_cards(self.front, 3):16s} │")
        lines.append(f"│ Middle ({len(self.middle)}/5): {_pad_cards(self.middle, 5):16s} │")
        lines.append(f"│ Back   ({len(self.back)}/5): {_pad_cards(self.back, 5):16s} │")
        lines.append("└─────────────────────────┘")
        if self.is_complete():
            if self.is_fouled():
                lines.append("  ⚠️  FOULED!")
            else:
                lines.append("  ✅ Valid board")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"OFCBoard(front=[{cards_to_str(self.front)}], "
            f"middle=[{cards_to_str(self.middle)}], "
            f"back=[{cards_to_str(self.back)}])"
        )


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------

@dataclass
class GameState:
    """Full game state for a Pineapple OFC hand."""

    board: OFCBoard = field(default_factory=OFCBoard)
    opponent_board: OFCBoard = field(default_factory=OFCBoard)
    hand: list[int] = field(default_factory=list)
    dead_cards: list[int] = field(default_factory=list)
    fantasyland: bool = False
    round_num: int = 0  # 0 = initial 5, 1+ = pineapple rounds

    @property
    def is_initial_deal(self) -> bool:
        """True if this is the first deal (5 cards)."""
        return self.round_num == 0

    @property
    def cards_to_place(self) -> int:
        """Number of cards that must be placed this round."""
        if self.is_initial_deal:
            return 5
        return 2  # Pineapple: pick 2 from 3

    @property
    def cards_to_discard(self) -> int:
        """Number of cards to discard this round."""
        if self.is_initial_deal:
            return 0
        return 1  # Pineapple: discard 1 from 3

    def all_known_cards(self) -> set[int]:
        """All cards that are known (on boards, in hand, or dead)."""
        known = set(self.board.all_cards())
        known.update(self.opponent_board.all_cards())
        known.update(self.hand)
        known.update(self.dead_cards)
        return known

    def copy(self) -> "GameState":
        return GameState(
            board=self.board.copy(),
            opponent_board=self.opponent_board.copy(),
            hand=list(self.hand),
            dead_cards=list(self.dead_cards),
            fantasyland=self.fantasyland,
            round_num=self.round_num,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pad_cards(cards: list[int], capacity: int) -> str:
    """Format cards for display, padding with dots for empty slots."""
    parts = [card_to_pretty(c) for c in cards]
    parts.extend(["··"] * (capacity - len(cards)))
    return " ".join(parts)
