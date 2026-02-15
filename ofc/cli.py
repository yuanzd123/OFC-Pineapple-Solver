"""
Interactive CLI for the OFC Pineapple Solver.

Commands:
  new           — Start a new hand
  board         — Show current board state
  initial <5c>  — Set initial 5 cards (e.g., 'initial Ah Kh Qh Jh Th')
  deal <3c>     — Deal 3 pineapple cards
  dead <cards>  — Mark dead/seen cards
  place <c> <r> — Manually place a card (r = front/middle/back)
  opp <c> <r>   — Place a card on opponent's board
  solve [n]     — Run solver with n simulations (default 3000)
  score         — Show current royalties and board score
  undo          — Undo last action
  help          — Show help
  quit          — Exit
"""

from __future__ import annotations

import sys
from typing import Optional

from ofc.board import GameState, OFCBoard, Row, ROW_NAMES
from ofc.card import (
    card_from_str,
    card_to_pretty,
    cards_from_str,
    cards_to_pretty,
)
from ofc.evaluator import hand_class_name_3, hand_class_name_5
from ofc.scoring import (
    estimate_royalties,
    qualifies_fantasyland,
    royalties_back,
    royalties_front,
    royalties_middle,
    total_royalties,
)
from ofc.solver import DEFAULT_SIMULATIONS, solve

ROW_ALIASES = {
    "front": Row.FRONT,
    "f": Row.FRONT,
    "top": Row.FRONT,
    "t": Row.FRONT,
    "middle": Row.MIDDLE,
    "m": Row.MIDDLE,
    "mid": Row.MIDDLE,
    "back": Row.BACK,
    "b": Row.BACK,
    "bottom": Row.BACK,
    "bot": Row.BACK,
}

HELP_TEXT = """
╔═══════════════════════════════════════════════════════╗
║             OFC Pineapple Solver CLI                  ║
╠═══════════════════════════════════════════════════════╣
║  new              Start a new hand                    ║
║  board            Show current board                  ║
║  initial <5c>     Initial 5 cards + get advice        ║
║  deal <3c>        3 pineapple cards + get advice      ║
║  dead <cards>     Mark dead/opponent cards             ║
║  place <c> <row>  Manually place card                 ║
║  opp <c> <row>    Place on opponent board              ║
║  solve [n]        Run solver (n = simulations)        ║
║  score            Show royalties & score              ║
║  undo             Undo last action                    ║
║  help             Show this help                      ║
║  quit / q         Exit                                ║
╠═══════════════════════════════════════════════════════╣
║  Cards: Ah Kc Td 9s 2h  (Rank + suit)               ║
║  Rows:  front/f  middle/m  back/b                    ║
╚═══════════════════════════════════════════════════════╝
"""


class OFCCli:
    """Interactive CLI for the OFC Pineapple solver."""

    def __init__(self) -> None:
        self.state = GameState()
        self.history: list[GameState] = []
        self.sim_count = DEFAULT_SIMULATIONS

    def run(self) -> None:
        print("\n🃏 OFC Pineapple Solver")
        print("  Type 'help' for commands, 'quit' to exit\n")
        self._show_board()

        while True:
            try:
                line = input("\nofc> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye!")
                break

            if not line:
                continue

            parts = line.split()
            cmd = parts[0].lower()
            args = parts[1:]

            try:
                if cmd in ("quit", "q", "exit"):
                    print("Bye!")
                    break
                elif cmd == "help":
                    print(HELP_TEXT)
                elif cmd == "new":
                    self._cmd_new()
                elif cmd == "board":
                    self._show_board()
                elif cmd == "initial":
                    self._cmd_initial(args)
                elif cmd == "deal":
                    self._cmd_deal(args)
                elif cmd == "dead":
                    self._cmd_dead(args)
                elif cmd == "place":
                    self._cmd_place(args)
                elif cmd == "opp":
                    self._cmd_opp(args)
                elif cmd == "solve":
                    self._cmd_solve(args)
                elif cmd == "score":
                    self._cmd_score()
                elif cmd == "undo":
                    self._cmd_undo()
                else:
                    print(f"Unknown command: '{cmd}'. Type 'help' for commands.")
            except Exception as e:
                print(f"Error: {e}")

    def _save_state(self) -> None:
        self.history.append(self.state.copy())

    def _cmd_new(self) -> None:
        self._save_state()
        self.state = GameState()
        print("New hand started.")
        self._show_board()

    def _cmd_initial(self, args: list[str]) -> None:
        cards = cards_from_str(" ".join(args))
        if len(cards) != 5:
            print(f"Need exactly 5 cards, got {len(cards)}")
            return

        self._save_state()
        self.state.hand = cards
        self.state.round_num = 0

        print(f"\nInitial hand: {cards_to_pretty(cards)}")
        print("Running solver...")
        result = solve(self.state, num_simulations=self.sim_count)
        print(result.display())

        # Auto-apply the best placement
        apply = input("\nApply best placement? [Y/n] ").strip().lower()
        if apply in ("", "y", "yes"):
            for p in result.placements:
                self.state.board.place_card(p.row, p.card)
            self.state.hand = []
            self.state.round_num = 1
            print("Placement applied.")
            self._show_board()

    def _cmd_deal(self, args: list[str]) -> None:
        cards = cards_from_str(" ".join(args))
        if len(cards) != 3:
            print(f"Need exactly 3 cards for pineapple deal, got {len(cards)}")
            return

        self._save_state()
        self.state.hand = cards
        if self.state.round_num == 0:
            self.state.round_num = 1

        print(f"\nPineapple deal: {cards_to_pretty(cards)}")
        print("Running solver...")
        result = solve(self.state, num_simulations=self.sim_count)
        print(result.display())

        apply = input("\nApply best placement? [Y/n] ").strip().lower()
        if apply in ("", "y", "yes"):
            for p in result.placements:
                self.state.board.place_card(p.row, p.card)
            if result.discard is not None:
                self.state.dead_cards.append(result.discard)
            self.state.hand = []
            self.state.round_num += 1
            print("Placement applied.")
            self._show_board()
            self._cmd_score()

    def _cmd_dead(self, args: list[str]) -> None:
        cards = cards_from_str(" ".join(args))
        self._save_state()
        self.state.dead_cards.extend(cards)
        print(f"Marked dead: {cards_to_pretty(cards)}")
        print(f"Total dead cards: {len(self.state.dead_cards)}")

    def _cmd_place(self, args: list[str]) -> None:
        if len(args) != 2:
            print("Usage: place <card> <row>  (e.g., 'place Ah front')")
            return

        card = card_from_str(args[0])
        row_name = args[1].lower()
        if row_name not in ROW_ALIASES:
            print(f"Invalid row: '{row_name}'. Use front/middle/back.")
            return

        row = ROW_ALIASES[row_name]
        self._save_state()
        self.state.board.place_card(row, card)
        print(f"Placed {card_to_pretty(card)} → {ROW_NAMES[row]}")
        self._show_board()

    def _cmd_opp(self, args: list[str]) -> None:
        if len(args) != 2:
            print("Usage: opp <card> <row>  (e.g., 'opp Ah front')")
            return

        card = card_from_str(args[0])
        row_name = args[1].lower()
        if row_name not in ROW_ALIASES:
            print(f"Invalid row: '{row_name}'. Use front/middle/back.")
            return

        row = ROW_ALIASES[row_name]
        self._save_state()
        self.state.opponent_board.place_card(row, card)
        print(f"Opponent: {card_to_pretty(card)} → {ROW_NAMES[row]}")

    def _cmd_solve(self, args: list[str]) -> None:
        n = int(args[0]) if args else self.sim_count
        if not self.state.hand:
            print("No cards in hand. Use 'initial' or 'deal' first.")
            return

        print(f"Running solver with {n} simulations...")
        result = solve(self.state, num_simulations=n)
        print(result.display())

    def _cmd_score(self) -> None:
        board = self.state.board
        print("\n  📊 Score Summary")

        if board.is_front_full():
            r = royalties_front(board.front)
            name = hand_class_name_3(board.front)
            print(f"  Front:  {cards_to_pretty(board.front)} — {name} (+{r} royalty)")

        if board.is_middle_full():
            r = royalties_middle(board.middle)
            name = hand_class_name_5(board.middle)
            print(f"  Middle: {cards_to_pretty(board.middle)} — {name} (+{r} royalty)")

        if board.is_back_full():
            r = royalties_back(board.back)
            name = hand_class_name_5(board.back)
            print(f"  Back:   {cards_to_pretty(board.back)} — {name} (+{r} royalty)")

        if board.is_complete():
            t = total_royalties(board)
            print(f"\n  Total Royalties: {t}")
            if board.is_fouled():
                print("  ⚠️  FOULED — all royalties lost!")
            if qualifies_fantasyland(board):
                print("  🎰 FANTASYLAND qualified!")

    def _cmd_undo(self) -> None:
        if not self.history:
            print("Nothing to undo.")
            return
        self.state = self.history.pop()
        print("Undone.")
        self._show_board()

    def _show_board(self) -> None:
        print("\n" + self.state.board.display())
        if self.state.hand:
            print(f"  Hand: {cards_to_pretty(self.state.hand)}")
        if self.state.dead_cards:
            print(f"  Dead: {cards_to_pretty(self.state.dead_cards)}")
