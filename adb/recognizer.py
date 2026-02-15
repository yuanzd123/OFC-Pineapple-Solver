"""
Card recognition using LLM Vision API.

Supports:
  - Ollama (local, free) — default, uses MiniCPM-o 4.5
  - OpenAI (cloud, paid) — GPT-4o fallback

Sends cropped screenshot regions to the vision model and
parses the response into card codes (e.g., 'Ah', 'Kc', 'Td').
"""

from __future__ import annotations

import base64
import io
import json
import re
import time
from typing import Optional

from PIL import Image

from adb.config import VisionConfig
from ofc.card import card_from_str


# ---------------------------------------------------------------------------
# Card recognition prompts
# ---------------------------------------------------------------------------

RECOGNIZE_HAND_PROMPT = """Look at this poker game screenshot. Identify ALL the playing cards visible in the player's HAND area (the cards that were just dealt to them at the bottom of the screen).

Return ONLY a JSON array of card codes, where each card is 2 characters:
- Rank: A, K, Q, J, T, 9, 8, 7, 6, 5, 4, 3, 2
- Suit: h (hearts), d (diamonds), c (clubs), s (spades)

Example: ["Ah", "Kc", "Td", "9s", "2h"]

If you cannot identify a card clearly, use "??" for that card.
Return ONLY the JSON array, no other text."""

RECOGNIZE_BOARD_PROMPT = """Look at this poker game screenshot. Identify ALL the playing cards placed on the player's board.

The board has 3 rows:
- Front (top row): up to 3 cards
- Middle (center row): up to 5 cards
- Back (bottom row): up to 5 cards

Return a JSON object with the cards in each row:
{
  "front": ["Ah", "Kc", "2d"],
  "middle": ["Ts", "9h", "8d", "7c", "6s"],
  "back": ["Qh", "Qd", "Qs", "Jh", "Jd"]
}

Use the same card code format (rank + suit). Use "??" for unclear cards.
Only include rows that have cards. Return ONLY the JSON, no other text."""

RECOGNIZE_ALL_PROMPT = """Look at this Open Face Chinese Poker (Pineapple) screenshot.
The screen is split into two areas:
1. OPPONENT (Top Half): Visible face-up cards here are "dead cards".
2. PLAYER (Bottom Half):
   - HAND: New cards dealt at the very bottom (3 or 5 cards).
   - BOARD: Player's 3 rows (Front/Middle/Back) above the hand.

Identify card codes (Rank + Suit, e.g., Ah, Td, 2s).
- Rank: A, K, Q, J, T, 9, 8, 7, 6, 5, 4, 3, 2
- Suit: h, d, c, s

Return a JSON object:
{
  "hand": ["Ah", "Kc", "Td"],       // Player's new cards (bottom)
  "board": {                         // Player's placed cards
    "front": [],
    "middle": [],
    "back": []
  },
  "opponent": ["Ks", "Qs", "Js"]     // All visible cards in TOP half
}

Use "??" for unclear cards. Return ONLY JSON."""


# ---------------------------------------------------------------------------
# Core recognizer
# ---------------------------------------------------------------------------

def recognize_cards_from_image(
    image: Image.Image,
    prompt: str = RECOGNIZE_ALL_PROMPT,
    config: VisionConfig | None = None,
) -> dict:
    """Send an image to LLM vision API and parse card recognition results.

    Returns parsed JSON response from the LLM.
    Also saves debug artifacts (image, prompt, response) to current dir.
    """
    cfg = config or VisionConfig()
    start = time.time()

    # Save debug image
    image.save("debug_last_scan.png")

    # Encode image to base64 PNG
    img_b64 = _image_to_base64(image, max_size=1024)

    # Save debug prompt
    with open("debug_last_prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt)

    # Call LLM API based on provider
    if cfg.provider == "ollama":
        response_text = _call_ollama_vision(img_b64, prompt, cfg)
    elif cfg.provider == "openai":
        response_text = _call_openai_vision(img_b64, prompt, cfg)
    else:
        raise ValueError(f"Unsupported provider: {cfg.provider}")

    # Save debug response
    with open("debug_last_result.txt", "w", encoding="utf-8") as f:
        f.write(response_text)

    elapsed = time.time() - start
    print(f"  🔍 Recognition: {elapsed:.2f}s (saved debug logs)")

    # Parse response
    return _parse_response(response_text)


def recognize_hand(
    image: Image.Image,
    config: VisionConfig | None = None,
) -> list[str]:
    """Recognize cards in the player's hand from a screenshot.

    Returns list of card strings like ['Ah', 'Kc', 'Td'].
    """
    result = recognize_cards_from_image(image, RECOGNIZE_HAND_PROMPT, config)
    if isinstance(result, list):
        return [c for c in result if c != "??"]
    return result.get("hand", [])


def recognize_all(
    image: Image.Image,
    config: VisionConfig | None = None,
) -> dict:
    """Recognize all visible cards (hand + board) from a screenshot.

    Returns dict with 'hand' and 'board' keys.
    """
    result = recognize_cards_from_image(image, RECOGNIZE_ALL_PROMPT, config)
    if not isinstance(result, dict):
        return {"hand": result if isinstance(result, list) else [], "board": {}}
    return result


def validate_cards(cards: list[str]) -> list[str]:
    """Validate card strings and return only valid ones."""
    valid = []
    for c in cards:
        if c == "??":
            continue
        try:
            card_from_str(c)
            valid.append(c)
        except ValueError:
            print(f"  ⚠️  Ignoring invalid card: {c}")
    return valid


# ---------------------------------------------------------------------------
# LLM API calls
# ---------------------------------------------------------------------------

def _call_ollama_vision(
    img_b64: str,
    prompt: str,
    config: VisionConfig,
) -> str:
    """Call Ollama local vision model via its OpenAI-compatible API."""
    try:
        from openai import OpenAI
        import httpx
    except ImportError:
        raise ImportError(
            "openai package required. Install with: pip install openai"
        )

    # Use a custom httpx client with NO proxy to avoid SOCKS proxy issues
    # when connecting to localhost Ollama server
    import os
    os.environ["NO_PROXY"] = os.environ.get("NO_PROXY", "") + ",localhost,127.0.0.1"
    http_client = httpx.Client(proxy=None)
    client = OpenAI(
        base_url=config.ollama_base_url,
        api_key="ollama",  # Ollama doesn't need a real key
        http_client=http_client,
    )

    response = client.chat.completions.create(
        model=config.model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_b64}",
                        },
                    },
                ],
            }
        ],
        max_tokens=config.max_tokens,
        timeout=config.timeout,
    )

    return response.choices[0].message.content.strip()


def _call_openai_vision(
    img_b64: str,
    prompt: str,
    config: VisionConfig,
) -> str:
    """Call OpenAI Vision API with an image."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "openai package required. Install with: pip install openai"
        )

    client = OpenAI(api_key=config.get_api_key())

    response = client.chat.completions.create(
        model=config.model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_b64}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
        max_tokens=config.max_tokens,
        timeout=config.timeout,
    )

    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _image_to_base64(img: Image.Image, max_size: int = 1024) -> str:
    """Convert PIL Image to base64 PNG string, resizing if needed.

    Resizing reduces API cost and latency without hurting card recognition.
    """
    # Resize if too large
    w, h = img.size
    if max(w, h) > max_size:
        scale = max_size / max(w, h)
        new_size = (int(w * scale), int(h * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _parse_response(text: str) -> dict | list:
    """Parse LLM response text into structured data.

    Handles JSON wrapped in markdown code blocks, plain JSON, etc.
    """
    # Strip markdown code block if present
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (```json and ```)
        text = "\n".join(lines[1:-1]).strip()

    # Try to parse as JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from text
    json_match = re.search(r'[\[{].*[\]}]', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Last resort: try to extract card codes with regex
    cards = re.findall(r'\b([AKQJT2-9][hdcs])\b', text, re.IGNORECASE)
    if cards:
        return cards

    raise ValueError(f"Could not parse card recognition response: {text}")
