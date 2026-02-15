#!/usr/bin/env python3
"""
OFC Pineapple Solver — Main Entry Point.

Usage:
  python main.py cli      Interactive CLI mode (type cards or use 'scan')
  python main.py solve    Quick solve from arguments
  python main.py watch    Hotkey-triggered screen reading mode
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
        # Quick solve: python main.py solve "Ah Kh Qh Jh Th"
        from ofc.card import cards_from_str, cards_to_pretty
        from ofc.board import GameState
        from ofc.solver import solve

        if len(sys.argv) < 3:
            print("Usage: python main.py solve <hand_cards> [--sims N]")
            print("Example: python main.py solve 'Ah Kh Qh Jh Th'")
            sys.exit(1)

        hand_str = sys.argv[2]
        cards = cards_from_str(hand_str)
        sims = 1500

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
        _run_watch_mode()

    else:
        print(f"Unknown mode: {mode}")
        print("Available modes: cli, solve, watch")
        sys.exit(1)


def _run_watch_mode() -> None:
    """Hotkey-triggered screen reading mode.

    Press Enter to trigger a scan (screenshot → recognize → solve).
    The solver maintains state across rounds automatically.
    """
    from ofc.cli import OFCCli

    print("\n🃏 OFC Pineapple Solver — Watch Mode")
    print("  Press ENTER to scan screen, 'q' to quit")
    print("  Make sure ADB is connected (run 'connect' in CLI first)\n")

    cli = OFCCli()
    cli._show_board()

    while True:
        try:
            line = input("\n[ENTER to scan, 'n' new hand, 'q' quit] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if line in ("q", "quit", "exit"):
            print("Bye!")
            break
        elif line in ("n", "new"):
            cli._cmd_new()
        elif line in ("b", "board"):
            cli._show_board()
        elif line in ("s", "score"):
            cli._cmd_score()
        elif line in ("u", "undo"):
            cli._cmd_undo()
        elif line == "":
            # Enter pressed — trigger scan
            try:
                cli._cmd_scan()
            except Exception as e:
                print(f"  ❌ Scan failed: {e}")
                print("  Try 'connect' in CLI mode to test ADB connection")
        else:
            # Allow typing cards directly as fallback
            parts = line.split()
            if len(parts) == 5:
                try:
                    cli._cmd_initial(parts)
                except Exception as e:
                    print(f"  Error: {e}")
            elif len(parts) == 3:
                try:
                    cli._cmd_deal(parts)
                except Exception as e:
                    print(f"  Error: {e}")
            else:
                print(f"  Unknown input. Press Enter to scan or type card codes.")


if __name__ == "__main__":
    main()
