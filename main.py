#!/usr/bin/env python3
"""
OFC Pineapple Solver — Main Entry Point.

Usage:
  python main.py cli      Interactive CLI mode
  python main.py solve    Quick solve from arguments
  python main.py watch    (future) ADB screen watching mode
  python main.py auto     (future) Full auto-play mode
"""

import sys


def main() -> None:
    if len(sys.argv) < 2:
        mode = "cli"
    else:
        mode = sys.argv[1].lower()

    if mode == "cli":
        from ofc.cli import OFCCli
        cli = OFCCli()
        cli.run()

    elif mode == "solve":
        # Quick solve: python main.py solve "Ah Kh Qh" "board_state..."
        from ofc.card import cards_from_str, cards_to_pretty
        from ofc.board import GameState
        from ofc.solver import solve

        if len(sys.argv) < 3:
            print("Usage: python main.py solve <hand_cards> [--sims N]")
            print("Example: python main.py solve 'Ah Kh Qh Jh Th'")
            sys.exit(1)

        hand_str = sys.argv[2]
        cards = cards_from_str(hand_str)
        sims = 3000

        # Parse optional arguments
        for i, arg in enumerate(sys.argv[3:], start=3):
            if arg == "--sims" and i + 1 < len(sys.argv):
                sims = int(sys.argv[i + 1])

        state = GameState()
        state.hand = cards
        state.round_num = 0 if len(cards) == 5 else 1

        print(f"Hand: {cards_to_pretty(cards)}")
        print(f"Running {sims} simulations...")

        result = solve(state, num_simulations=sims)
        print(result.display())

    elif mode == "watch":
        print("Watch mode coming soon (Phase 2)")
        print("This will use ADB to capture the screen and suggest moves")

    elif mode == "auto":
        print("Auto-play mode coming soon (Phase 3)")
        print("This will use ADB to capture, solve, and auto-place cards")

    else:
        print(f"Unknown mode: {mode}")
        print("Available modes: cli, solve, watch, auto")
        sys.exit(1)


if __name__ == "__main__":
    main()
