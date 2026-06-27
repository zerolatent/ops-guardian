from __future__ import annotations

import base64
from pathlib import Path
import struct
import sys
import zlib

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ops_guardian.config import get_settings


def make_png_data_url() -> str:
    width = 32
    height = 32
    raw_rows = []
    for _y in range(height):
        row = bytearray([0])
        for _x in range(width):
            row.extend([220, 38, 38])
        raw_rows.append(bytes(row))
    raw = b"".join(raw_rows)

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    encoded = base64.b64encode(png).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def main() -> None:
    settings = get_settings()
    if not settings.openai_api_key or not settings.vision_model:
        raise SystemExit("OPENAI_API_KEY and VISION_MODEL must be configured.")

    response = httpx.post(
        f"{settings.openai_base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Answer only the dominant color in the image. Do not explain."},
                        {"type": "image_url", "image_url": {"url": make_png_data_url()}},
                    ],
                }
            ],
            "temperature": 0,
            "max_tokens": 512,
            "think": False,
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    choice = payload["choices"][0]
    message = choice["message"].get("content") or ""
    finish_reason = choice.get("finish_reason")
    if message.strip():
        print(message.strip())
    else:
        message_keys = sorted(choice.get("message", {}).keys())
        reasoning = (
            choice.get("message", {}).get("reasoning_content")
            or choice.get("message", {}).get("thinking")
            or choice.get("message", {}).get("reasoning")
        )
        if reasoning:
            print(f"EMPTY_CONTENT finish_reason={finish_reason} message_keys={message_keys} reasoning={str(reasoning)[:300]}")
        else:
            print(f"EMPTY_CONTENT finish_reason={finish_reason} message_keys={message_keys}")


if __name__ == "__main__":
    main()
