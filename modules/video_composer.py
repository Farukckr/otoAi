"""
Video birlestirici modul.
Gorselleri ve videolari ses ile birlestirerek dikey formatta kisa video uretir.
"""
import json
import os
import random
import textwrap
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import config

try:
    from moviepy import (
        AudioFileClip,
        ColorClip,
        CompositeVideoClip,
        ImageClip,
        VideoFileClip,
        CompositeAudioClip,
    )
    import moviepy.video.fx as vfx
    import moviepy.audio.fx as afx

    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    print("MoviePy yuklu degil. Video kompozisyonu devre disi.")


TARGET_W = config.VIDEO_WIDTH
TARGET_H = config.VIDEO_HEIGHT
FPS = config.VIDEO_FPS


def _safe_close(clip) -> None:
    """MoviePy clip'lerini sessizce kapat."""
    if clip is None:
        return

    try:
        clip.close()
    except Exception:
        pass


def _resize_to_fill(clip, target_w: int, target_h: int):
    """Clip'i hedef boyuta sigacak sekilde kirpar ve buyutur."""
    clip_ratio = clip.w / clip.h
    target_ratio = target_w / target_h

    if clip_ratio > target_ratio:
        new_h = target_h
        new_w = int(clip_ratio * new_h)
    else:
        new_w = target_w
        new_h = int(new_w / clip_ratio)

    clip = clip.resized((new_w, new_h))

    x_center = new_w // 2
    y_center = new_h // 2
    clip = clip.cropped(
        x1=x_center - target_w // 2,
        y1=y_center - target_h // 2,
        x2=x_center + target_w // 2,
        y2=y_center + target_h // 2,
    )
    return clip


def turkish_upper(text: str) -> str:
    """Turkce i/I donusumunu dogru yapan upper fonksiyonu. Noktalama isaretlerini korur."""
    # i -> İ ve ı -> I dönüşümü yapıp sonra standart upper çağırıyoruz
    # Ancak punctuation karakterlerine dokunmuyoruz.
    result = text.replace("i", "İ").replace("ı", "I").upper()
    return result


def _create_subtitle_image(text: str, width: int = TARGET_W, highlight_word_idx: int = -1) -> np.ndarray:
    """
    Karaoke tarzı altyazı görseli.
    highlight_word_idx: -1 ise tüm kelimeler sarı, ≥ 0 ise o indeksteki kelime kırmızı.
    """
    font_size = 110
    font = None
    font_paths = [
        "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/trebucbd.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except Exception:
                continue

    if font is None:
        font = ImageFont.load_default()

    # Metni kelimelere ayır (Boşluklara göre ayırırken noktalamayı kelimeye yapışık tutar)
    lines = textwrap.wrap(text, width=15, break_long_words=False, replace_whitespace=False) or [""]
    line_spacing = 20
    total_text_h = len(lines) * font_size + (len(lines) - 1) * line_spacing
    box_height = total_text_h + 100

    img = Image.new("RGBA", (width, box_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    current_y = (box_height - total_text_h) // 2

    # Kelimelerin hangi satırda olduğunu takip edelim
    word_global_idx = 0

    for line in lines:
        line_words = line.split()
        # Satırın tamamının genişliğini hesapla (kontur için)
        full_bbox = draw.textbbox((0, 0), line, font=font)
        full_text_w = full_bbox[2] - full_bbox[0]
        line_x = (width - full_text_w) // 2

        # Kelime kelime boyayalım
        cursor_x = line_x
        for i, word in enumerate(line_words):
            # Bu kelimenin global indeksini bul
            is_highlight = (word_global_idx == highlight_word_idx)
            # Daha şık renk paleti: Aktif için derin bir kırmızı, pasif için temiz off-white
            color = (255, 40, 40, 255) if is_highlight else (250, 250, 245, 255)

            # 1. Yumuşak Alt Gölge (Drop Shadow)
            shadow_offset = 5
            draw.text(
                (cursor_x + shadow_offset, current_y + shadow_offset), 
                word, 
                font=font, 
                fill=(0, 0, 0, 160)
            )

            # 2. Ana metin ve pürüzsüz dış kontur (Stroke)
            draw.text(
                (cursor_x, current_y), 
                word, 
                font=font, 
                fill=color, 
                stroke_width=6, 
                stroke_fill=(0, 0, 0, 255)
            )

            # Kelime genişliğini hesapla ve boşluk ekle
            w_bbox = draw.textbbox((0, 0), word + " ", font=font)
            cursor_x += w_bbox[2] - w_bbox[0]
            word_global_idx += 1

        current_y += font_size + line_spacing

    return np.array(img)


def _load_asset(asset_path: Path, duration: float):
    """Video veya fotografi MoviePy clip'ine yukler."""
    path_str = str(asset_path)
    ext = asset_path.suffix.lower()

    if ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
        try:
            clip = VideoFileClip(path_str)
            clip = clip.without_audio()

            if clip.duration > duration:
                clip = clip.subclipped(0, duration)
            else:
                clip = clip.with_effects([vfx.Loop(duration=duration)])

            return _resize_to_fill(clip, TARGET_W, TARGET_H)
        except Exception as e:
            print(f"Video yuklenemedi ({asset_path.name}): {e}")
            return None

    if ext in [".jpg", ".jpeg", ".png", ".webp"]:
        try:
            clip = ImageClip(path_str, duration=duration)
            return _resize_to_fill(clip, TARGET_W, TARGET_H)
        except Exception as e:
            print(f"Fotograf yuklenemedi ({asset_path.name}): {e}")
            return None

    return None


def compose_video(
    assets: list[Path],
    audio_path: Path,
    script: dict,
    output_path: Path,
    scene_plan: dict = None,
) -> Optional[Path]:
    """Tum bilesenleri birlestirip final videoyu uretir."""
    if not MOVIEPY_AVAILABLE:
        print("MoviePy yuklu degil, video olusturulamadi.")
        return None

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("Video birlestiriliyor...")

    narration_audio = None
    output_audio = None
    final_video = None
    bg_clips = []
    overlay_clips = []
    bg_music = None
    
    try:
        narration_audio = AudioFileClip(str(audio_path))
        total_duration = narration_audio.duration

        print(f"  Toplam sure: {total_duration:.1f} saniye")
        print(f"  Asset sayisi: {len(assets)}")

        clip_duration = total_duration / max(len(assets), 1)
        clip_duration = min(clip_duration, 8.0)

        current_time = 0.0
        
        if scene_plan and "scenes" in scene_plan:
            print("  Akıllı sahne planı kullanılıyor (Dynamic Exact Cuts with Crossfades)")
            for i, sc in enumerate(scene_plan["scenes"]):
                asset_path = sc.get("selected_asset")
                if not asset_path:
                    continue
                
                sc_start = float(sc.get("start_hint", current_time))
                sc_end = float(sc.get("end_hint", sc_start + clip_duration))
                
                # Eğer bu son sahneyse, bitiş saniyesini videonun gerçek (ses) bitişine kadar uzat!
                # Böylece videonun en sonunda siyah ekran çıkmaz.
                if i == len(scene_plan["scenes"]) - 1:
                    sc_end = max(sc_end, total_duration)
                
                # Sınırları aşmayı engelle
                if sc_start >= total_duration:
                    break
                    
                # Akıcı Geçiş (Crossfade) Süresi: sadece ilk klip değilse uygula
                crossfade_dur = 0.3 if i > 0 else 0.0
                
                # Crossfade boyunca bir önceki klibin üzerine binmesi için süreye crossfade_dur ekleriz
                sc_dur = sc_end - sc_start + crossfade_dur
                sc_dur = max(sc_dur, 0.5)  # En az yarım saniye
                dur = min(sc_dur, total_duration - sc_start + crossfade_dur)
                
                clip = _load_asset(Path(asset_path), dur)
                if clip:
                    try:
                        # Hafif zoom (kenardan çok içeri girmeden premium bir his)
                        clip = clip.resized(
                            lambda t: 1.0 + 0.03 * (t / max(dur, 1.0))
                        ).with_position("center")
                    except Exception:
                        pass

                    # Bu klip crossfade_dur kadar erken başlayacak (öncekiyle örtüşecek)
                    start_pos = max(0.0, sc_start - crossfade_dur)
                    clip = clip.with_start(start_pos)
                    
                    if crossfade_dur > 0 and start_pos > 0:
                        clip = clip.with_effects([vfx.CrossFadeIn(crossfade_dur)])
                        
                    bg_clips.append(clip)
                current_time = sc_start + (dur - crossfade_dur)
        else:
            # Eski eşit bölme mantığı (Fallback)
            asset_cycle = []
            if assets:
                repeat_count = int(total_duration / max(clip_duration * len(assets), 0.001)) + 2
                asset_cycle = assets * repeat_count

            for asset in asset_cycle:
                remaining = total_duration - current_time
                if remaining <= 0:
                    break

                dur = min(clip_duration, remaining)
                clip = _load_asset(asset, dur)

                if clip:
                    try:
                        clip = clip.resized(
                            lambda t: 1.0 + 0.05 * (t / max(dur, 1.0))
                        ).with_position("center")
                    except Exception:
                        pass

                    clip = clip.with_start(current_time)
                    bg_clips.append(clip)
                    current_time += dur

        if not bg_clips:
            print("Uygun asset bulunamadi, duz renk arka plan kullaniliyor.")
            bg_clips = [ColorClip((TARGET_W, TARGET_H), color=(20, 20, 30), duration=total_duration)]

        full_text = script.get("full_script", "")
        if not full_text:
            full_text = (
                script.get("hook", "")
                + " "
                + " ".join(script.get("story_parts", []))
                + " "
                + script.get("cta", "")
            )

        # Karaoke altyazı sistemi: kelime bazlı kırmızı vurgulama
        timestamps_path = audio_path.with_suffix(".json")
        word_timestamps = []
        if timestamps_path.exists():
            with open(timestamps_path, "r", encoding="utf-8") as f:
                word_timestamps = json.load(f)
            print(f"  🎤 {len(word_timestamps)} kelime zamanlaması yüklendi (karaoke mod)")

        if word_timestamps:
            # Kelimeleri 2-3'lü gruplara böl
            group_size = 2
            groups = []
            for i in range(0, len(word_timestamps), group_size):
                group = word_timestamps[i:i + group_size]
                groups.append(group)

            for group in groups:
                if not group:
                    continue

                group_start = group[0]["start"]
                group_end = group[-1]["end"]
                group_duration = max(group_end - group_start, 0.1)

                if group_start >= total_duration:
                    break

                # Grubun tüm kelimelerini birleştir
                group_text = turkish_upper(" ".join(w["word"] for w in group))
                group_words = group_text.split()

                # Her kelime için ayrı bir vurgulu kare oluştur
                for wi, word_info in enumerate(group):
                    word_start = word_info["start"]
                    word_end = word_info["end"]
                    word_dur = max(word_end - word_start, 0.05)

                    if word_start >= total_duration:
                        break

                    # Son kelime mi kontrol et
                    is_last_word = (group == groups[-1] and wi == len(group) - 1)
                    if is_last_word:
                        word_dur = max(word_dur, total_duration - word_start)

                    sub_img = _create_subtitle_image(group_text, highlight_word_idx=wi)
                    sub_clip = ImageClip(sub_img)
                    sub_clip = sub_clip.with_position(("center", TARGET_H // 2 + 100))
                    
                    sub_clip = sub_clip.with_duration(
                        min(word_dur, total_duration - word_start)
                    ).with_start(word_start)
                    overlay_clips.append(sub_clip)

        elif full_text:
            # Fallback: timestamp yoksa eski yöntemle çalış
            words = full_text.split()
            chunks = []
            current_chunk = []

            for word in words:
                current_chunk.append(word)
                if len(current_chunk) >= 2 or word.endswith((",", ".", "!", "?")) or len(word) > 10:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []

            if current_chunk:
                chunks.append(" ".join(current_chunk))

            total_chars = sum(len(chunk) for chunk in chunks)
            current_time = 0.0

            for chunk in chunks:
                if current_time >= total_duration:
                    break

                chunk_dur = total_duration * (len(chunk) / max(total_chars, 1))
                sub_img = _create_subtitle_image(turkish_upper(chunk))
                sub_clip = ImageClip(sub_img)
                sub_clip = sub_clip.with_position(("center", TARGET_H // 2 + 100))
                sub_clip = sub_clip.with_duration(
                    min(chunk_dur, total_duration - current_time)
                ).with_start(current_time)
                overlay_clips.append(sub_clip)
                current_time += chunk_dur

        final_video = CompositeVideoClip(bg_clips + overlay_clips, size=(TARGET_W, TARGET_H))
        final_video = final_video.with_duration(total_duration)

        output_audio = narration_audio.subclipped(0, total_duration)
        
        # Arka plan müziği ekle
        music_folder = Path("assets/music")
        if music_folder.exists():
            music_files = list(music_folder.glob("*.mp3")) + list(music_folder.glob("*.wav"))
            if music_files:
                try:
                    music_path = random.choice(music_files)
                    print(f"Arka plan müziği ekleniyor: {music_path.name}")
                    bg_music = AudioFileClip(str(music_path))
                    
                    # Müziği döngüye al ve süresini ayarla
                    bg_music = bg_music.with_effects([vfx.Loop(duration=total_duration)])
                    
                    # Ses seviyesini %12 civarına düşür (Konuşmanın önüne geçmesin)
                    bg_music = bg_music.with_volume_scaled(0.12)
                    
                    # Ana ses ile birleştir
                    output_audio = CompositeAudioClip([output_audio, bg_music])
                except Exception as e:
                    print(f"Müzik eklenirken hata oluştu: {e}")
        
        final_video = final_video.with_audio(output_audio)

        print(f"Video kaydediliyor: {output_path}")
        final_video.write_videofile(
            str(output_path),
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=str(config.TEMP_DIR / f"temp_audio_{random.randint(1000, 9999)}.m4a"),
            remove_temp=True,
            logger=None,
            preset="fast",
            ffmpeg_params=["-crf", "23"],
        )

        print(f"Video hazir: {output_path}")
        return output_path
    finally:
        _safe_close(final_video)
        _safe_close(output_audio)
        _safe_close(narration_audio)
        _safe_close(bg_music)

        for clip in overlay_clips:
            _safe_close(clip)

        for clip in bg_clips:
            _safe_close(clip)
