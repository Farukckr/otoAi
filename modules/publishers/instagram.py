"""
Instagram Reels yükleyici.
instagrapi kullanarak videoları otomatik yükler.
"""
import os
import json
import pickle
import time
from pathlib import Path
from typing import Optional

try:
    from instagrapi import Client
    INSTAGRAM_AVAILABLE = True
except ImportError:
    INSTAGRAM_AVAILABLE = False

import config

SESSION_FILE = config.BASE_DIR / "instagram_session.json"

def _get_instagram_client():
    """Instagram istemcisini döndürür. Oturumu dosyadan yükler veya yeni giriş yapar."""
    if not INSTAGRAM_AVAILABLE:
        raise ImportError("instagrapi kütüphanesi yüklü değil. 'pip install instagrapi' komutunu çalıştırın.")
    
    if not config.INSTAGRAM_USERNAME or not config.INSTAGRAM_PASSWORD:
        raise ValueError("Instagram kullanıcı adı veya şifresi config.py içinde ayarlanmamış.")

    cl = Client()
    
    # Session yükle (varsa)
    if SESSION_FILE.exists():
        try:
            cl.load_settings(SESSION_FILE)
            print("✅ Instagram: Mevcut oturum yüklendi.")
        except Exception as e:
            print(f"⚠️ Instagram oturum yükleme hatası: {e}. Yeniden giriş yapılıyor...")

    # Giriş yap (gerekirse)
    try:
        # cl.get_settings() session'ın geçerli olup olmadığını kontrol etmez, 
        # sadece yüklendiğini gösterir. Bir işlem yaparak kontrol edelim.
        cl.get_timeline_feed()
    except Exception:
        print(f"🔑 Instagram: Giriş yapılıyor ({config.INSTAGRAM_USERNAME})...")
        try:
            cl.login(config.INSTAGRAM_USERNAME, config.INSTAGRAM_PASSWORD)
            cl.dump_settings(SESSION_FILE)
            print("✅ Instagram: Giriş başarılı ve oturum kaydedildi.")
        except Exception as e:
            print(f"❌ Instagram giriş hatası: {e}")
            raise

    return cl

def upload_reels(
    video_path: Path,
    caption: str,
    hashtags: list[str] = None
) -> Optional[str]:
    """
    Instagram'a Reels videosu yükler.
    
    Args:
        video_path: Yüklenecek video dosyası
        caption: Video açıklaması
        hashtags: Hashtag listesi
    
    Returns:
        Media ID veya None (hata durumunda)
    """
    if not config.INSTAGRAM_UPLOAD_ENABLED:
        print("ℹ️ Instagram yükleme devre dışı.")
        return None

    try:
        cl = _get_instagram_client()
    except Exception as e:
        print(f"❌ Instagram bağlantı hatası: {e}")
        return None
    
    # Açıklama oluştur
    tags_str = " ".join(hashtags) if hashtags else ""
    full_caption = f"{caption}\n\n{tags_str}\n\n#reels #shorts"
    
    print(f"📤 Instagram'a yükleniyor (Reels): {caption[:50]}...")
    
    try:
        # Reels olarak yükle
        media = cl.clip_upload(
            str(video_path),
            caption=full_caption
        )
        
        media_id = media.pk
        print(f"✅ Instagram'a yüklendi! PK: {media_id}")
        return media_id
    
    except Exception as e:
        print(f"❌ Instagram yükleme hatası: {e}")
        return None

def upload_reels_simple(video_path: Path, script: dict) -> Optional[str]:
    """Script verisinden otomatik upload - kolaylaştırılmış arayüz."""
    # Eğer özel instagram açıklaması varsa onu kullan, yoksa başlığı kullan
    caption = script.get("instagram_caption") or script.get("title", "İlginç Bilgiler")
    return upload_reels(
        video_path=video_path,
        caption=caption,
        hashtags=script.get("hashtags", ["#viral", "#türkçe", "#bilgi"])
    )

if __name__ == "__main__":
    # Test amaçlı direkt çalıştırılabilir
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("video", help="Test edilecek video yolu")
    args = parser.parse_args()
    
    if os.path.exists(args.video):
        test_script = {"title": "Test Videosu", "hashtags": ["#test", "#otoai"]}
        upload_reels_simple(Path(args.video), test_script)
    else:
        print("Video dosyası bulunamadı.")
