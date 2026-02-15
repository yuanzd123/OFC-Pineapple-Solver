"""
Semi-auto OFC Pineapple Solver CLI.

Streamlined for real-time play:
  1. Type 'initial Ah Kh Qh Jh 2c' → solver auto-places best option
  2. Type 'deal Ts 9c 3d' → solver places 2, discards 1
  3. Or use 'scan' to auto-capture from screen via ADB + LLM Vision
  4. Repeat until hand is complete
"""

from __future__ import annotations

import sys
import time

from ofc.board import GameState, OFCBoard, Row, ROW_NAMES
from ofc.card import (
    card_from_str,
    card_to_pretty,
    cards_from_str,
    cards_to_pretty,
)
from ofc.evaluator import hand_class_name_3, hand_class_name_5
from ofc.scoring import (
    qualifies_fantasyland,
    royalties_back,
    royalties_front,
    royalties_middle,
    total_royalties,
)
from ofc.solver import solve

# Simulation counts tuned for speed: initial <5s, pineapple <3s
INITIAL_SIMS = 1000
PINEAPPLE_SIMS = 1500

HELP_TEXT = """
┌─────────────────────────────────────────┐
│       OFC Pineapple Solver              │
├─────────────────────────────────────────┤
│  Manual Input:                          │
│  initial <5c>   First 5 cards           │
│  deal <3c>      Pineapple 3 cards       │
│  dead <cards>   Mark dead cards         │
├─────────────────────────────────────────┤
│  Screen Reading:                        │
│  connect         Test ADB connection    │
│  scan            Screenshot → solve     │
│  save            Save screenshot        │
├─────────────────────────────────────────┤
│  General:                               │
│  new             Start new hand         │
│  board           Show board             │
│  score           Show royalties         │
│  undo            Undo last round        │
│  quit            Exit                   │
├─────────────────────────────────────────┤
│  Cards: Ah Kc Td 9s 2h                 │
│  Example: initial Ah Kh Qh Jh 2c       │
│  Or just type 'scan' to read screen!    │
└─────────────────────────────────────────┘
"""


class OFCCli:
    """Semi-auto OFC Pineapple solver CLI."""

    def __init__(self, config=None) -> None:
        self.state = GameState()
        self.history: list[GameState] = []
        self._config = config  # adb.config.Config, loaded lazily

    def run(self) -> None:
        print("\n🃏 OFC Pineapple Solver (semi-auto)")
        print("  Type 'help' for commands\n")
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
                elif cmd in ("initial", "init", "i"):
                    self._cmd_initial(args)
                elif cmd in ("deal", "d"):
                    self._cmd_deal(args)
                elif cmd == "dead":
                    self._cmd_dead(args)
                elif cmd == "board":
                    self._show_board()
                elif cmd == "score":
                    self._cmd_score()
                elif cmd == "undo":
                    self._cmd_undo()
                elif cmd == "connect":
                    self._cmd_connect()
                elif cmd == "scan":
                    self._cmd_scan()
                elif cmd == "save":
                    self._cmd_save(args)
                else:
                    print(f"Unknown: '{cmd}'. Type 'help'.")
            except Exception as e:
                print(f"Error: {e}")

    def _save_state(self) -> None:
        self.history.append(self.state.copy())

    def _cmd_new(self) -> None:
        self._save_state()
        self.state = GameState()
        print("✨ New hand started.")
        self._show_board()

    def _cmd_initial(self, args: list[str]) -> None:
        cards = cards_from_str(" ".join(args))
        if len(cards) != 5:
            print(f"Need 5 cards, got {len(cards)}")
            return

        self._save_state()
        self.state.hand = cards
        self.state.round_num = 0

        print(f"  Hand: {cards_to_pretty(cards)}")
        print(f"  Solving ({INITIAL_SIMS} sims)...", end=" ", flush=True)

        result = solve(self.state, num_simulations=INITIAL_SIMS)
        print(f"done in {result.elapsed_seconds:.1f}s")

        # Auto-apply best placement
        for p in result.placements:
            self.state.board.place_card(p.row, p.card)
        self.state.hand = []
        self.state.round_num = 1

        # Show result
        self._show_recommendation(result)
        self._show_board()

    def _cmd_deal(self, args: list[str]) -> None:
        cards = cards_from_str(" ".join(args))
        if len(cards) != 3:
            print(f"Need 3 cards, got {len(cards)}")
            return

        self._save_state()
        self.state.hand = cards
        if self.state.round_num == 0:
            self.state.round_num = 1

        print(f"  Deal: {cards_to_pretty(cards)}")
        print(f"  Solving ({PINEAPPLE_SIMS} sims)...", end=" ", flush=True)

        result = solve(self.state, num_simulations=PINEAPPLE_SIMS)
        print(f"done in {result.elapsed_seconds:.1f}s")

        # Auto-apply best placement
        for p in result.placements:
            self.state.board.place_card(p.row, p.card)
        if result.discard is not None:
            self.state.dead_cards.append(result.discard)
        self.state.hand = []
        self.state.round_num += 1

        # Show result
        self._show_recommendation(result)
        self._show_board()
        self._cmd_score()

    def _cmd_dead(self, args: list[str]) -> None:
        cards = cards_from_str(" ".join(args))
        self._save_state()
        self.state.dead_cards.extend(cards)
        print(f"  Dead: {cards_to_pretty(cards)} (total: {len(self.state.dead_cards)})")

    def _cmd_score(self) -> None:
        board = self.state.board
        if board.is_front_full():
            r = royalties_front(board.front)
            name = hand_class_name_3(board.front)
            print(f"  Front:  {cards_to_pretty(board.front)} — {name} (+{r})")
        if board.is_middle_full():
            r = royalties_middle(board.middle)
            name = hand_class_name_5(board.middle)
            print(f"  Middle: {cards_to_pretty(board.middle)} — {name} (+{r})")
        if board.is_back_full():
            r = royalties_back(board.back)
            name = hand_class_name_5(board.back)
            print(f"  Back:   {cards_to_pretty(board.back)} — {name} (+{r})")
        if board.is_complete():
            t = total_royalties(board)
            if board.is_fouled():
                print(f"  ⚠️  FOULED — all royalties lost!")
            else:
                print(f"  Total: {t} royalties")
                if qualifies_fantasyland(board):
                    print("  🎰 FANTASYLAND!")

    def _cmd_undo(self) -> None:
        if not self.history:
            print("Nothing to undo.")
            return
        self.state = self.history.pop()
        print("↩ Undone.")
        self._show_board()

    def _show_recommendation(self, result) -> None:
        """Show the solver's recommendation compactly."""
        print("  ═══ Best Move ═══")
        for p in result.placements:
            print(f"    {card_to_pretty(p.card)} → {p.row.name}")
        if result.discard is not None:
            print(f"    Discard: {card_to_pretty(result.discard)}")
        print(f"    EV: {result.expected_value:.2f}")

        # Show top 3 alternatives
        if len(result.all_options) > 1:
            print("  ─── Alternatives ───")
            for i, (placements, discard, ev) in enumerate(result.all_options[1:4]):
                desc = " ".join(f"{card_to_pretty(p.card)}→{p.row.name}" for p in placements)
                disc = f" disc:{card_to_pretty(discard)}" if discard is not None else ""
                print(f"    {i+2}. {desc}{disc} EV={ev:.2f}")

    def _show_board(self) -> None:
        print("\n" + self.state.board.display())
        if self.state.dead_cards:
            print(f"  Dead: {cards_to_pretty(self.state.dead_cards)}")

    # ------------------------------------------------------------------
    # Screen reading commands
    # ------------------------------------------------------------------

    def _get_config(self):
        """Lazy-load ADB config."""
        if self._config is None:
            from adb.config import Config
            self._config = Config.default()
        return self._config

    def _cmd_connect(self) -> None:
        """Test ADB connection."""
        from adb.screen import check_adb
        cfg = self._get_config()
        ok, msg = check_adb(cfg.adb)
        if ok:
            print(f"  ✅ {msg}")
        else:
            print(f"  ❌ {msg}")

    def _cmd_scan(self) -> None:
        """Take screenshot, recognize cards via LLM, and auto-solve."""
        from adb.screen import capture_screenshot, crop_region
        from adb.recognizer import recognize_all, validate_cards

        cfg = self._get_config()

        # 1. Capture screenshot
        print("  Scanning screen...")
        img = capture_screenshot(cfg.adb)

        # 2. Crop to relevant region if configured
        if cfg.layout.hand_region:
            crop_img = crop_region(img, cfg.layout.hand_region)
        else:
            crop_img = img  # Send full screen

        # 3. Recognize cards via LLM
        result = recognize_all(crop_img, cfg.vision)

        hand_cards = validate_cards(result.get("hand", []))
        board_data = result.get("board", {})
        opponent_cards = validate_cards(result.get("opponent", []))

        if board_data:
            # Flatten/validate board cards to avoid list-in-list errors
            for row_key in ["front", "middle", "back"]:
                if row_key in board_data:
                    board_data[row_key] = validate_cards(board_data[row_key])

        print(f"  Recognized hand: {' '.join(hand_cards)}")
        if board_data:
            for row_name, row_cards in board_data.items():
                if row_cards:
                    print(f"  Recognized {row_name}: {' '.join(row_cards)}")
        if opponent_cards:
            print(f"  Recognized opponent (dead): {' '.join(opponent_cards)}")
            # Add opponent cards to dead cards list
            self.state.dead_cards.extend(card_from_str(c) for c in opponent_cards)

        print("  (Debug logs saved to: debug_last_scan.png, _prompt.txt, _result.txt)")

        if not hand_cards:
            print("  ⚠️  No cards recognized in hand. Check debug_last_scan.png.")
            return

        # 4. Auto-apply recognized cards as initial or deal
        self._save_state()
        cards = cards_from_str(" ".join(hand_cards))

        if len(cards) == 5 and self.state.board.total_cards() == 0:
            # Initial deal
            self.state.hand = cards
            self.state.round_num = 0
            print(f"  Hand: {cards_to_pretty(cards)}")
            print(f"  Solving ({INITIAL_SIMS} sims)...", end=" ", flush=True)
            solve_result = solve(self.state, num_simulations=INITIAL_SIMS)
            print(f"done in {solve_result.elapsed_seconds:.1f}s")
            for p in solve_result.placements:
                self.state.board.place_card(p.row, p.card)
            self.state.hand = []
            self.state.round_num = 1
            self._show_recommendation(solve_result)
            self._show_board()

        elif len(cards) == 3:
            # Pineapple deal
            self.state.hand = cards
            if self.state.round_num == 0:
                self.state.round_num = 1
            print(f"  Deal: {cards_to_pretty(cards)}")
            print(f"  Solving ({PINEAPPLE_SIMS} sims)...", end=" ", flush=True)
            solve_result = solve(self.state, num_simulations=PINEAPPLE_SIMS)
            print(f"done in {solve_result.elapsed_seconds:.1f}s")
            for p in solve_result.placements:
                self.state.board.place_card(p.row, p.card)
            if solve_result.discard is not None:
                self.state.dead_cards.append(solve_result.discard)
            self.state.hand = []
            self.state.round_num += 1
            self._show_recommendation(solve_result)
            self._show_board()
            self._cmd_score()

        else:
            print(f"  ⚠️  Expected 5 (initial) or 3 (pineapple) cards, got {len(cards)}")
            self.state = self.history.pop()  # Undo save

    def _cmd_save(self, args: list[str]) -> None:
        """Save a screenshot for debugging/calibration.
        
        Usage: save [filename]
        If no filename provided, saves as screenshot_YYYYMMDD_HHMMSS.png
        """
        from adb.screen import capture_screenshot, save_screenshot
        import datetime

        if args:
            filename = args[0]
            if not filename.endswith(".png"):
                filename += ".png"
        else:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        
        cfg = self._get_config()
        img = capture_screenshot(cfg.adb)
        save_screenshot(img, filename)
        print(f"  💾 Saved to {filename}")

