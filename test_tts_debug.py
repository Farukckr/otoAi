"""
TTS WordBoundary test script.
edge-tts WordBoundary ve generate_speech() fonksiyonunu test eder.
"""
import asyncio
import sys
import json
from pathlib import Path

# ── Windows konsol UTF-8 güvenliği ──
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import edge_tts


async def test_raw_wordboundary() -> int:
    """edge-tts WordBoundary olaylarini dogrudan test et."""
    TEXT = "Buz neden kaygandır? Su donunca genişler."
    VOICE = "tr-TR-AhmetNeural"
    print(f"\n[Test 1] Raw WordBoundary — {VOICE}")
    print(f"  Metin: {TEXT}")

    communicate = edge_tts.Communicate(TEXT, VOICE, boundary="WordBoundary")
    count = 0
    async for chunk in communicate.stream():
        if chunk["type"] == "WordBoundary":
            start = chunk["offset"] / 10_000_000
            dur = chunk["duration"] / 10_000_000
            print(f"  {count+1}. '{chunk['text']}' @ {start:.3f}s (dur={dur:.3f}s)")
            count += 1
    print(f"  Toplam: {count} kelime")
    return count


def test_generate_speech() -> int:
    """generate_speech() fonksiyonunu test et, JSON ciktisini dogrula."""
    print("\n[Test 2] generate_speech() fonksiyonu")

    # Projeyi import et
    sys.path.insert(0, str(Path(__file__).parent))
    from modules.tts_engine import generate_speech

    out = Path("temp/test_karaoke.mp3")
    generate_speech("Buz neden kaygandır? Su donunca genişler.", out)

    json_path = out.with_suffix(".json")
    if not json_path.exists():
        print(f"  HATA: JSON dosyasi olusturulamadi: {json_path}")
        return 0

    data = json.load(open(json_path, "r", encoding="utf-8"))
    print(f"  JSON: {len(data)} kelime zamanlama")

    if data:
        print(f"  Ilk kelime: '{data[0]['word']}' @ {data[0]['start']}s")
        print(f"  Son kelime: '{data[-1]['word']}' @ {data[-1]['start']}s - {data[-1]['end']}s")
    else:
        print("  UYARI: JSON bos!")

    return len(data)


if __name__ == "__main__":
    # Test 1: Raw WordBoundary
    raw_count = asyncio.run(test_raw_wordboundary())

    # Test 2: generate_speech (ayri bir asyncio.run cagirdi ici yapiyor)
    gen_count = test_generate_speech()

    # Sonuc
    print("\n" + "=" * 40)
    print(f"Test 1 (Raw):            {raw_count} kelime")
    print(f"Test 2 (generate_speech): {gen_count} kelime")
    ok = raw_count > 0 and gen_count > 0
    print(f"Sonuc: {'BASARILI' if ok else 'BASARISIZ'}")
    print("=" * 40)
