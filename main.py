"""
Ana video uretim pipeline'i.
Tum modulleri sirayla calistirarak tam video uretir.
"""
import json
import shutil
import sys
import os
import time
from datetime import datetime, timedelta

import config
from modules.asset_fetcher import fetch_assets_for_scene_plan
from modules.content_ai import generate_script, get_random_topic
from modules.publishers.youtube import upload_video_simple
from modules.publishers.instagram import upload_reels_simple
from modules.scene_planner import generate_scene_plan
from modules.tts_engine import generate_speech
from modules.video_composer import compose_video


def cleanup_old_files(max_age_days: int = 7):
    """Output klasorundeki 7 gunlukten eski dosya ve klasorleri siler."""
    print(f"\n🧹 Temizlik yapiliyor ({max_age_days} gunden eski dosyalar)...")
    
    now = time.time()
    cutoff = now - (max_age_days * 86400)  # 86400 saniye = 1 gun
    
    count = 0
    if not config.OUTPUT_DIR.exists():
        return

    for item in config.OUTPUT_DIR.iterdir():
        # Dosya/Klasorun olusturulma zamani (ctime Windows'ta olusturma, Unix'te metadata degisimi)
        # st_mtime (degistirilme) kullanmak daha garanti olabilir.
        item_time = item.stat().st_mtime
        
        if item_time < cutoff:
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
                count += 1
                print(f"  - Silindi: {item.name}")
            except Exception as e:
                print(f"  - HATA: {item.name} silinemedi: {e}")
    
    if count > 0:
        print(f"✅ Toplam {count} adet eski dosya temizlendi.")
    else:
        print("✨ Eski dosya bulunamadi, temizlenecek bir sey yok.")


def create_video(topic: str = None, upload: bool = True) -> dict:
    """Tam video uretim pipeline'i."""
    print("\n" + "=" * 60)
    print("Video uretim basliyor...")
    print("=" * 60)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = config.TEMP_DIR / f"session_{timestamp}"
    session_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "timestamp": timestamp,
        "status": "failed",
        "video_path": None,
        "youtube_id": None,
    }

    try:
        if not topic:
            topic = get_random_topic()

        print(f"\nKonu: {topic}")
        script = generate_script(topic)
        result["title"] = script["title"]
        result["topic"] = topic

        # 2. TTS ve Kelime Zamanlamaları
        audio_path = session_dir / "narration.mp3"
        generate_speech(script["full_script"], audio_path)

        timestamps_path = audio_path.with_suffix(".json")
        word_timestamps = []
        if timestamps_path.exists():
            with open(timestamps_path, "r", encoding="utf-8") as f:
                word_timestamps = json.load(f)

        # 3. Akıllı Sahne Planlama
        scene_plan = generate_scene_plan(script, word_timestamps)
        
        # 4. Puanlamalı Asset Arama (Sahne planına göre)
        scene_plan = fetch_assets_for_scene_plan(
            scene_plan=scene_plan,
            temp_dir=session_dir / "assets"
        )

        output_filename = f"video_{timestamp}.mp4"
        output_path = config.OUTPUT_DIR / output_filename

        # 5. Video Birleştirme
        video_path = compose_video(
            assets=[],  # Akıllı plan kullanıldığı için boş verilebilir
            audio_path=audio_path,
            script=script,
            output_path=output_path,
            scene_plan=scene_plan,
        )

        if not video_path:
            raise RuntimeError("Video olusturulamadi.")

        result["video_path"] = str(video_path)
        result["status"] = "created"

        meta_path = config.OUTPUT_DIR / f"meta_{timestamp}.json"
        
        # Script ve Scene Plan'i birleştirip kaydet
        final_meta = script.copy()
        final_meta["scene_plan"] = scene_plan
        
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(final_meta, f, ensure_ascii=False, indent=2)

        print("\nVideo basariyla olusturuldu!")
        print(f"  {video_path}")

        if upload:
            print("\nYouTube'a yukleniyor...")
            video_id = upload_video_simple(video_path, script)

            if video_id:
                result["youtube_id"] = video_id
                result["youtube_url"] = f"https://www.youtube.com/shorts/{video_id}"
                result["status"] = "published"
                print(f"  https://www.youtube.com/shorts/{video_id}")
            else:
                print("  Bilgi: YouTube yukleme atlandi.")

            if config.INSTAGRAM_UPLOAD_ENABLED:
                print("\nInstagram Reels'e yukleniyor...")
                ig_media_id = upload_reels_simple(video_path, script)
                if ig_media_id:
                    result["instagram_id"] = ig_media_id
                    result["status"] = "published"  # Hem YT hem IG veya sadece IG olsa da "published"
                    print(f"  Instagram basarili! ID: {ig_media_id}")
                else:
                    print("  Bilgi: Instagram yukleme basarisiz veya atlandi.")

        print("\n" + "=" * 60)
        print("ISLEM TAMAMLANDI")
        print("=" * 60)

    except Exception as e:
        print(f"\nHata: {e}")
        import traceback

        traceback.print_exc()
        result["error"] = str(e)

    finally:
        try:
            shutil.rmtree(session_dir)
        except FileNotFoundError:
            pass
        except Exception as cleanup_error:
            warning = f"Gecici klasor temizlenemedi: {session_dir} ({cleanup_error})"
            print(f"\nUYARI: {warning}")
            result["cleanup_warning"] = warning

        if session_dir.exists() and "cleanup_warning" not in result:
            warning = f"Gecici klasor kaldi: {session_dir}"
            print(f"\nUYARI: {warning}")
            result["cleanup_warning"] = warning

    return result


def run_daily_pipeline():
    """Gunluk otomatik video uretimi icin calistirilir."""
    print(f"\nGunluk pipeline basladi: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Once eski dosyalari temizle
    cleanup_old_files(max_age_days=7)

    for i in range(config.VIDEOS_PER_DAY):
        if config.VIDEOS_PER_DAY > 1:
            print(f"\n--- Video {i + 1}/{config.VIDEOS_PER_DAY} ---")

        result = create_video(upload=True)

        log_file = config.BASE_DIR / "production_log.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI Video Uretici")
    parser.add_argument("--topic", type=str, help="Belirli bir konu")
    parser.add_argument("--no-upload", action="store_true", help="YouTube yuklemesini kapat")
    parser.add_argument("--test", action="store_true", help="Test modu")
    args = parser.parse_args()

    config.validate_config()

    # Manuel calistirmada da temizlik yap
    cleanup_old_files(max_age_days=7)

    result = create_video(topic=args.topic, upload=not args.no_upload)

    if result["status"] in ("created", "published"):
        print("\nBasarili!")
        sys.exit(0)

    print(f"\nBasarisiz: {result.get('error', 'Bilinmeyen hata')}")
    sys.exit(1)
