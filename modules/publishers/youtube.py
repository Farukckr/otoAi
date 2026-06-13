"""
YouTube Shorts yükleyici.
YouTube Data API v3 kullanarak videoları otomatik yükler.
"""
import os
import json
import pickle
from pathlib import Path
from typing import Optional

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

import config

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = config.BASE_DIR / "youtube_token.pickle"
CREDENTIALS_FILE = config.BASE_DIR / "youtube_credentials.json"


def _get_youtube_service():
    """YouTube API servisini döndürür. İlk kullanımda OAuth akışını başlatır."""
    if not GOOGLE_AVAILABLE:
        raise ImportError("Google API kütüphaneleri yüklü değil.")
    
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"YouTube credentials dosyası bulunamadı: {CREDENTIALS_FILE}\n"
            "Google Cloud Console'dan OAuth2 credentials indirip bu isimle kaydedin."
        )
    
    creds = None
    
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
    
    return build("youtube", "v3", credentials=creds)


def upload_video(
    video_path: Path,
    title: str,
    description: str,
    hashtags: list[str],
    privacy: str = config.YOUTUBE_PRIVACY
) -> Optional[str]:
    """
    YouTube'a video yükler.
    
    Args:
        video_path: Yüklenecek video dosyası
        title: Video başlığı
        description: Video açıklaması
        hashtags: Hashtag listesi
        privacy: 'public', 'private', veya 'unlisted'
    
    Returns:
        YouTube video ID'si veya None (hata durumunda)
    """
    try:
        youtube = _get_youtube_service()
    except FileNotFoundError as e:
        print(f"⚠️  YouTube credentials eksik: {e}")
        print("  YouTube yükleme atlanıyor...")
        return None
    except Exception as e:
        print(f"❌ YouTube bağlantı hatası: {e}")
        return None
    
    # Açıklama oluştur
    tags_str = " ".join(hashtags) if hashtags else ""
    full_description = f"{description}\n\n{tags_str}\n\n#shorts"
    
    # Tags listesi (YouTube için virgülle ayrı)
    tags = [tag.lstrip("#") for tag in hashtags] + ["shorts", "türkçe", "viral"]
    
    body = {
        "snippet": {
            "title": title[:100],  # YouTube max 100 karakter
            "description": full_description[:5000],
            "tags": tags[:30],  # Max 30 tag
            "categoryId": config.YOUTUBE_CATEGORY_ID,
            "defaultLanguage": "tr",
            "defaultAudioLanguage": "tr"
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False
        }
    }
    
    media = MediaFileUpload(
        str(video_path),
        chunksize=1024 * 1024,  # 1MB chunks
        resumable=True,
        mimetype="video/mp4"
    )
    
    print(f"📤 YouTube'a yükleniyor: {title[:50]}...")
    
    try:
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                print(f"  Yükleniyor: %{progress}")
        
        video_id = response["id"]
        video_url = f"https://www.youtube.com/shorts/{video_id}"
        print(f"✅ YouTube'a yüklendi!")
        print(f"  🔗 {video_url}")
        return video_id
    
    except Exception as e:
        print(f"❌ YouTube yükleme hatası: {e}")
        return None


def upload_video_simple(video_path: Path, script: dict) -> Optional[str]:
    """Script verisinden otomatik upload - kolaylaştırılmış arayüz."""
    return upload_video(
        video_path=video_path,
        title=script.get("title", "İlginç Bilgiler"),
        description=script.get("youtube_description", script.get("full_script", "")),
        hashtags=script.get("hashtags", ["#viral", "#türkçe", "#bilgi"]),
        privacy=config.YOUTUBE_PRIVACY
    )
