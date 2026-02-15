"""
Card and Deck representation for OFC Pineapple.

Cards use a compact integer encoding for fast comparison:
  rank: 2=0, 3=1, ..., A=12
  suit: clubs=0, diamonds=1, hearts=2, spades=3
  card_int: rank * 4 + suit  (0..51)
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RANK_CHARS = "23456789TJQKA"
SUIT_CHARS = "cdhs"

RANK_MAP: dict[str, int] = {c: i for i, c in enumerate(RANK_CHARS)}
SUIT_MAP: dict[str, int] = {c: i for i, c in enumerate(SUIT_CHARS)}

RANK_NAMES = [
    "Two", "Three", "Four", "Five", "Six", "Seven",
    "Eight", "Nine", "Ten", "Jack", "Queen", "King", "Ace",
]
SUIT_NAMES = ["Clubs", "Diamonds", "Hearts", "Spades"]
SUIT_SYMBOLS = ["♣", "♦", "♥", "♠"]


# ---------------------------------------------------------------------------
# Card helpers  (card = int 0..51)
# ---------------------------------------------------------------------------

def card_rank(card: int) -> int:
    """Return the rank index (0=2 .. 12=A) of a card."""
    return card >> 2


def card_suit(card: int) -> int:
    """Return the suit index (0=c, 1=d, 2=h, 3=s) of a card."""
    return card & 3


def card_from_str(s: str) -> int:
    """Parse a 2-char string like 'Ah', 'Tc', '2d' into a card int.

    Case-insensitive for suits. Handles '10' as 'T'.
    """
    # Handle "10h" -> "Th"
    if len(s) == 3 and s.startswith("10"):
        s = "T" + s[2:]

    if len(s) != 2:
        raise ValueError(f"Invalid card string '{s}', must be 2 chars (e.g. 'Ah')")
    rank_ch, suit_ch = s[0].upper(), s[1].lower()
    if rank_ch not in RANK_MAP:
        raise ValueError(f"Invalid rank '{rank_ch}', expected one of {RANK_CHARS}")
    if suit_ch not in SUIT_MAP:
        raise ValueError(f"Invalid suit '{suit_ch}', expected one of {SUIT_CHARS}")
    return RANK_MAP[rank_ch] * 4 + SUIT_MAP[suit_ch]


def card_to_str(card: int) -> str:
    """Convert a card int back to a 2-char string like 'Ah'."""
    return RANK_CHARS[card_rank(card)] + SUIT_CHARS[card_suit(card)]


def card_to_pretty(card: int) -> str:
    """Pretty-print a card with suit symbol, e.g. 'A♥'."""
    return RANK_CHARS[card_rank(card)] + SUIT_SYMBOLS[card_suit(card)]


def cards_from_str(s: str) -> list[int]:
    """Parse a space-separated string of cards, e.g. 'Ah Kh Qh Jh Th'.

    Also accepts comma-separated.
    """
    s = s.replace(",", " ")
    tokens = s.split()
    return [card_from_str(t) for t in tokens]


def cards_to_str(cards: Sequence[int]) -> str:
    """Convert a list of card ints to a space-separated string."""
    return " ".join(card_to_str(c) for c in cards)


def cards_to_pretty(cards: Sequence[int]) -> str:
    """Pretty-print a list of cards with suit symbols."""
    return " ".join(card_to_pretty(c) for c in cards)


# ---------------------------------------------------------------------------
# Deck
# ---------------------------------------------------------------------------

class Deck:
    """A standard 52-card deck that tracks remaining cards."""

    def __init__(self) -> None:
        self._remaining: set[int] = set(range(52))

    @property
    def remaining(self) -> set[int]:
        return self._remaining

    @property
    def size(self) -> int:
        return len(self._remaining)

    def remove(self, *cards: int) -> None:
        """Remove specific cards from the deck (already dealt / dead)."""
        for c in cards:
            self._remaining.discard(c)

    def remove_str(self, s: str) -> None:
        """Remove cards specified as a string, e.g. 'Ah Kh'."""
        for c in cards_from_str(s):
            self._remaining.discard(c)

    def deal(self, n: int = 1) -> list[int]:
        """Deal n random cards from the remaining deck."""
        if n > len(self._remaining):
            raise ValueError(
                f"Cannot deal {n} cards, only {len(self._remaining)} remaining"
            )
        dealt = random.sample(sorted(self._remaining), n)
        for c in dealt:
            self._remaining.discard(c)
        return dealt

    def copy(self) -> "Deck":
        """Create a copy of this deck with the same remaining cards."""
        d = Deck.__new__(Deck)
        d._remaining = set(self._remaining)
        return d

    def __contains__(self, card: int) -> bool:
        return card in self._remaining

    def __repr__(self) -> str:
        return f"Deck({self.size} remaining)"
