"""
Pexels API üzerinden stok görsel ve video çeken modül.
Ücretsiz API ile yüksek kaliteli içerikler indirir.
"""
import requests
import random
import re
from pathlib import Path
from typing import Optional
import config


PEXELS_BASE_URL = "https://api.pexels.com"


def _get_headers() -> dict:
    return {"Authorization": config.PEXELS_API_KEY}


def search_videos(keyword: str, count: int = 5) -> list[dict]:
    """
    Pexels'da video arar ve sonuçları döndürür.
    
    Args:
        keyword: Arama kelimesi
        count: Kaç video döndürülsün
    
    Returns:
        Video meta verileri listesi
    """
    url = f"{PEXELS_BASE_URL}/videos/search"
    params = {
        "query": keyword,
        "orientation": "portrait",  # Dikey format
        "size": "medium",
        "per_page": max(count, 10),
        "locale": "en-US"
    }
    
    try:
        response = requests.get(url, headers=_get_headers(), params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("videos", [])[:count]
    except Exception as e:
        print(f"⚠️  Pexels video hatası: {e}")
        return []


def search_photos(keyword: str, count: int = 10) -> list[dict]:
    """Pexels'da fotoğraf arar."""
    url = f"{PEXELS_BASE_URL}/v1/search"
    params = {
        "query": keyword,
        "orientation": "portrait",
        "size": "large",
        "per_page": count,
        "locale": "en-US"
    }
    
    try:
        response = requests.get(url, headers=_get_headers(), params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("photos", [])[:count]
    except Exception as e:
        print(f"⚠️  Pexels fotoğraf hatası: {e}")
        return []


def download_video(video_data: dict, output_path: Path) -> Optional[Path]:
    """En uygun kalitede video dosyasını indirir."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # En iyi kaliteyi seç (HD tercih et)
    video_files = video_data.get("video_files", [])
    best = None
    
    for vf in video_files:
        if vf.get("quality") in ["hd", "sd"]:
            if best is None or (vf.get("width", 0) > best.get("width", 0)):
                best = vf
    
    if not best and video_files:
        best = video_files[0]
    
    if not best:
        return None
    
    url = best["link"]
    
    try:
        print(f"⬇️  Video indiriliyor: {output_path.name}")
        resp = requests.get(url, stream=True, timeout=30)
        resp.raise_for_status()
        
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Video indirildi: {output_path}")
        return output_path
    except Exception as e:
        print(f"❌ Video indirme hatası: {e}")
        return None


def download_photo(photo_data: dict, output_path: Path) -> Optional[Path]:
    """Fotoğrafı indirir."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    url = photo_data["src"].get("portrait") or photo_data["src"].get("large")
    
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        
        with open(output_path, "wb") as f:
            f.write(resp.content)
        
        return output_path
    except Exception as e:
        print(f"❌ Fotoğraf indirme hatası: {e}")
        return None


def fetch_assets_for_video(keywords: list[str], temp_dir: Path, num_clips: int = 5) -> list[Path]:
    """
    Video için gerekli görselleri/videoları toplar.
    Keyword'leri sırayla dener, yeterli video bulana kadar devam eder.
    """
    print(f"🔍 Asset aranıyor: {keywords}")
    temp_dir = Path(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    downloaded = []
    downloaded_urls = set()
    
    import itertools
    if not keywords:
        keywords = ["interesting facts", "did you know"]
        
    keyword_cycle = itertools.cycle(keywords)
    
    attempts = 0
    max_attempts = num_clips * 3
    
    while len(downloaded) < num_clips and attempts < max_attempts:
        attempts += 1
        keyword = next(keyword_cycle)
        
        # Önce video dene
        videos = search_videos(keyword, count=10)
        
        # Daha önce indirilmemiş videoları filtrele ve rastgele birini seç
        available_vids = [v for v in videos if v["id"] not in downloaded_urls]
        new_vid = None
        if available_vids:
            # En iyi eşleşmeyi kaybetmemek için ilk 3-4 taneden rastgele seç
            new_vid = random.choice(available_vids[:min(4, len(available_vids))])
                
        if new_vid:
            # Dosya adı için geçersiz karakterleri temizle (Windows için *, ?, :, \ vb.)
            clean_keyword = re.sub(r'[\\/*?:"<>|]', "", keyword).strip()[:30]
            filename = f"clip_{len(downloaded)}_{clean_keyword.replace(' ', '_')}.mp4"
            out = temp_dir / filename
            result = download_video(new_vid, out)
            if result:
                downloaded.append(result)
                downloaded_urls.add(new_vid["id"])
                continue
                
        # Video bulunamazsa fotoğraf indir
        photos = search_photos(keyword, count=10)
        new_photo = None
        for photo in photos:
            if photo["id"] not in downloaded_urls:
                new_photo = photo
                break
                
        if new_photo:
            out = temp_dir / f"photo_{len(downloaded)}_{keyword[:15].replace(' ', '_')}.jpg"
            result = download_photo(new_photo, out)
            if result:
                downloaded.append(result)
                downloaded_urls.add(new_photo["id"])
    
    print(f"✅ {len(downloaded)} asset indirildi")
    return downloaded


def _score_video(video_meta: dict, required_duration: float) -> int:
    """Video için uygunluk puanı hesaplar."""
    score = 0
    vid_duration = video_meta.get("duration", 0)
    
    # Süre puanı
    if vid_duration >= required_duration:
        score += 40
    elif vid_duration >= required_duration * 0.7:
        score += 15
    else:
        # Çok kısası istenmez
        score -= 20

    # Çözünürlük puanı
    v_files = video_meta.get("video_files", [])
    max_w = 0
    max_h = 0
    for vf in v_files:
        if vf.get("width", 0) > max_w:
            max_w = vf["width"]
            max_h = vf["height"]
            
    if max_h >= 1920 or max_w >= 1080:
        score += 30
    elif max_h >= 1280 or max_w >= 720:
        score += 10
    else:
        score -= 10
        
    # Vertical (dikey) oran kontrolü
    if max_h > max_w:
        score += 20
        
    return score


def fetch_assets_for_scene_plan(scene_plan: dict, temp_dir: Path) -> list:
    """
    Sahne planına (JSON) göre asset'leri arar, puanlar ve indirir.
    Returns:
       scene_plan (JSON verisi, içine selected_asset alanı eklenmiş olarak)
    """
    temp_dir = Path(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    downloaded_urls = set()
    
    scenes = scene_plan.get("scenes", [])
    print(f"🔍 Sahne planı için varlık aranıyor ({len(scenes)} sahne)...")
    
    for i, scene in enumerate(scenes):
        queries = scene.get("search_queries", [])
        if not queries:
            queries = [scene.get("primary_subject", "abstract satisfying loop")]
            
        req_dur = scene.get("end_hint", 5.0) - scene.get("start_hint", 0.0)
        # Biraz pay bırakalım (0.5 saniye)
        req_dur = max(req_dur + 0.5, 3.0)
        
        best_candidate = None
        best_score = -9999
        selected_query = ""
        
        print(f"  Sahne {i+1}: Sorgular deneniyor => {queries}")
        
        # Her query için arama yap ve puanla
        for query in queries:
            videos = search_videos(query, count=6)
            for v in videos:
                if v["id"] in downloaded_urls:
                    continue  # Daha önce seçildi, tekrarı engelle
                    
                score = _score_video(v, req_dur)
                if score > best_score:
                    best_score = score
                    best_candidate = v
                    selected_query = query
                    
            # Yeterince iyi bir video bulduysak (puan > 50) aramayı durdur
            if best_score >= 60:
                break
                
        # Eğer hiç bulunamadıysa (best_candidate hala None) fotoğraf dene (fallback)
        if not best_candidate:
            print(f"    Uygun video bulunamadı, fallback (fotoğraf) deneniyor...")
            for query in queries:
                photos = search_photos(query, count=5)
                for p in photos:
                    if p["id"] not in downloaded_urls:
                        # Dummy video verisi gibi yapıp score artır
                        best_candidate = p
                        selected_query = query
                        best_score = 10
                        break
                if best_candidate:
                    break
                    
        # İndirme işlemi
        if best_candidate:
            # Fotoğraf mı Video mu anla
            is_photo = "src" in best_candidate
            safe_query = re.sub(r'[\\/*?:"<>|]', "", selected_query).replace(" ", "_")[:20]
            
            if is_photo:
                out_path = temp_dir / f"scene_{i+1}_{safe_query}.jpg"
                res = download_photo(best_candidate, out_path)
            else:
                out_path = temp_dir / f"scene_{i+1}_{safe_query}.mp4"
                res = download_video(best_candidate, out_path)
                
            if res:
                downloaded_urls.add(best_candidate["id"])
                scene["selected_asset"] = str(res)
                scene["selected_query"] = selected_query
                scene["selection_reason"] = f"Skor: {best_score}"
            else:
                scene["selected_asset"] = None
        else:
            print(f"    Sahne {i+1} için hiçbir asset bulunamadı!")
            scene["selected_asset"] = None
            
    print(f"✅ {len(downloaded_urls)} benzersiz asset seçildi ve indirildi.")
    return scene_plan
