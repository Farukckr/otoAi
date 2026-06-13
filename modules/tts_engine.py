"""
TTS (Text-to-Speech) motoru.
Microsoft Edge-TTS (ÜCRETSİZ) kullanarak Türkçe seslendirme üretir.
Kelime bazlı zaman damgaları (WordBoundary) ile karaoke altyazı desteği sağlar.
"""
import asyncio
import json
import sys
from pathlib import Path
import edge_tts

# Türkçe ses seçenekleri:
# tr-TR-AhmetNeural  → Erkek
# Türkçe ses seçenekleri:
# tr-TR-AhmetNeural  → Erkek
# tr-TR-EmelNeural   → Kadın
TTS_VOICE = "tr-TR-AhmetNeural"
TTS_RATE = "+4%"    # Hızlı okuma yerine daha duraksamalı ve vurgulu akış için hızı düşürdük
TTS_PITCH = "-2Hz"  # Erkek sesine biraz daha derinlik ve sinematik otorite katmak için pitch'i azalttık

# ── Windows konsol güvenliği ──
def _safe_print(*args, **kwargs):
    """Emoji / Türkçe karakter hatasına dayanıklı print."""
    try:
        print(*args, **kwargs)
    except (UnicodeEncodeError, OSError):
        text = " ".join(str(a) for a in args)
        print(text.encode("utf-8", errors="replace").decode("ascii", errors="replace"))

# Retry sabitleri
_MAX_RETRIES = 3


async def _generate_with_timestamps(text: str, output_path: Path) -> list[dict]:
    """
    Edge-TTS ile ses üretir VE kelime bazlı zaman damgalarını döndürür.
    Her kelime için: {"word": str, "start": float (saniye), "end": float (saniye)}
    Ağ hataları nedeniyle boş dönerse yeniden dener (en fazla 3 kez).
    """
    last_error = None

    for attempt in range(1, _MAX_RETRIES + 1):
        # edge-tts 7.x varsayilan olarak SentenceBoundary donuyor.
        # Karaoke icin kelime bazli zaman damgalarini acikca istemeliyiz.
        communicate = edge_tts.Communicate(
            text,
            TTS_VOICE,
            rate=TTS_RATE,
            pitch=TTS_PITCH,
            boundary="WordBoundary",
        )
        word_timestamps = []

        try:
            # Dosyayı baştan oluştur
            with open(str(output_path), "wb") as f:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        # Offset ve duration 100ns (tick) cinsinden
                        start_sec = chunk["offset"] / 10_000_000
                        duration_sec = chunk["duration"] / 10_000_000
                        end_sec = start_sec + duration_sec

                        word_timestamps.append({
                            "word": chunk["text"],
                            "start": round(start_sec, 3),
                            "end": round(end_sec, 3),
                        })
        except Exception as exc:
            last_error = exc
            _safe_print(f"  [TTS] Deneme {attempt}/{_MAX_RETRIES} basarisiz: {exc}")
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(1)      # kısa bekleme, sonra tekrar dene
                continue
            # Son denemede de hata varsa boş döndür (ses dosyası kısmen kayıtlı olabilir)

        if word_timestamps:
            if attempt > 1:
                _safe_print(f"  [TTS] Basarili (deneme {attempt})")
            return word_timestamps

        # Boş geldiyse tekrar dene
        _safe_print(
            f"  [TTS] Deneme {attempt}/{_MAX_RETRIES}: "
            f"Hic WordBoundary alinamadi, {'tekrar deneniyor...' if attempt < _MAX_RETRIES else 'vazgeciliyor.'}"
        )
        if attempt < _MAX_RETRIES:
            await asyncio.sleep(1)

    _safe_print("  !! UYARI: Tum denemelerde kelime zamanlama alinamadi (WordBoundary eksik)")
    return word_timestamps   # boş liste


def generate_speech(text: str, output_path: Path) -> Path:
    """
    Metni sese çevirir ve dosyaya kaydeder.
    Tamamen ücretsiz — Microsoft Edge altyapısını kullanır.
    Kelime zamanlamaları da .json dosyasına kaydedilir.
    """
    _safe_print(f"Seslendirme uretiyor... ({len(text)} karakter)")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Eğer dosya varsa temizle
    if output_path.exists():
        output_path.unlink()

    # Async fonksiyonu çalıştır ve zaman damgalarını al
    word_timestamps = asyncio.run(_generate_with_timestamps(text, output_path))

    # Zaman damgalarını JSON olarak kaydet (video_composer okuyacak)
    timestamps_path = output_path.with_suffix(".json")
    with open(timestamps_path, "w", encoding="utf-8") as f:
        json.dump(word_timestamps, f, ensure_ascii=False, indent=2)

    _safe_print(f"Ses dosyasi: {output_path}")
    _safe_print(f"{len(word_timestamps)} kelime zamanlama kaydedildi")
    return output_path


def get_audio_duration(audio_path: Path) -> float:
    """Ses dosyasının süresini tahmin eder."""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(str(audio_path))
        return len(audio) / 1000.0
    except Exception:
        return 45.0
