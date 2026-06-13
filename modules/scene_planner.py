"""
Akıllı Sahne Planlama Modülü.
Metni anlamsal sahnelere (hook, story, cta vb.) ayırır.
Her sahne için görsel niyet, arama sorguları ve tam saniye (start/end) üretir.
Gemini 2.0 Flash modeli kullanır.
"""
import json
import re
from typing import List, Dict, Any
from google import genai
import config


def _clean_text_for_mapping(text: str) -> str:
    """Noktalama işaretlerini ve tagleri temizler, küçük harfe çevirir."""
    # Tagleri temizle [HIZLI], *kelime* vb.
    text = re.sub(r'\[.*?\]', '', text)
    text = text.replace('*', '')
    text = text.replace('.', '').replace(',', '').replace('?', '').replace('!', '').replace(';', '').replace('...', '')
    text = re.sub(r'\s+', ' ', text).strip()
    return text.lower()


def map_timestamps_to_scenes(scenes: List[Dict[str, Any]], word_timestamps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    LLM'den gelen sahne cümlelerini, TTS'in ürettiği word_timestamps ile
    eşleştirerek her sahnenin başlangıç ve bitiş saniyesini hesaplar.
    """
    if not word_timestamps or not scenes:
        return scenes

    word_idx = 0
    total_words = len(word_timestamps)

    for i, scene in enumerate(scenes):
        scene_text = scene.get("scene_text", "")
        # Sahne metnindeki kelimeleri say (yaklaşık)
        clean_scene = _clean_text_for_mapping(scene_text)
        scene_words = clean_scene.split()
        scene_word_count = len(scene_words)

        if scene_word_count == 0:
            continue

        # Başlangıç zamanı mevcut kelimenin start'ı
        if word_idx < total_words:
            scene["start_hint"] = word_timestamps[word_idx].get("start", 0.0)
        else:
            scene["start_hint"] = word_timestamps[-1].get("start", 0.0) if word_timestamps else 0.0

        # İleri sar
        word_idx += scene_word_count

        # Sınır kontrolü (LLM fazladan/eksik kelime saymış olabilir veya sayılar farklı yazılmış olabilir)
        if word_idx >= total_words:
            word_idx = total_words
            
        # Eğer bu son sahneyse doğrudan en son kelimeye git
        if i == len(scenes) - 1:
            word_idx = total_words

        # Bitiş zamanı bir önceki kelimenin end'i
        if word_idx > 0 and word_idx <= total_words:
            scene["end_hint"] = word_timestamps[word_idx - 1].get("end", scene["start_hint"] + 2.0)
        else:
            scene["end_hint"] = scene["start_hint"] + 2.0
            
    return scenes


def generate_scene_plan(script_data: Dict[str, Any], word_timestamps: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Script metnini alıp, gelişmiş bir prompt ile analiz ederek JSON sahne planı üretir.
    Eğer word_timestamps verilmişse, sahnelere kesin `start_hint` ve `end_hint` ekler.
    """
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    
    topic = script_data.get("topic", "Genel Kısa Video")
    full_script = script_data.get("full_script", "")
    
    if not full_script:
        # Fallback
        full_script = f"{script_data.get('hook', '')} {' '.join(script_data.get('story_parts', []))} {script_data.get('cta', '')}"

    system_prompt = """Sen uzman bir "Video Prodüktörü" ve "Stok Video Küratörü"sün. 
Görevin, okunan kısa video metnini (script) analiz edip, stok video araması için akıllı bir "Sahne Planı" (Scene Plan) oluşturmak.

KURALLAR:
1. Sahne Bölme Mantığı (Chunking):
- Metni mantıksal cümle gruplarına veya anlam bütünlüğü olan sahnelere böl.
- Aşırı kısa sahneler yapma (en azından 3-5 kelime olsun). Çok uzun cümleleri, görsel değişim gerektiriyorsa böl.
- İlk cümleyi mutlaka 'hook' sahnesi yap. Son cümleyi 'cta' sahnesi yap.

2. Sahne Sayısı Kararı:
- Sadece 5 sahneye kısıtlama! Metnin uzunluğuna, vurgu değişimine ve kısa video temposuna (TikTok/Shorts dinamizmine) göre sahne sayısını esnek belirle (genelde 4-8 arası).

3. Görsel Niyet ve Arama Sorguları (Visual Intent & Search Queries):
- Her sahnenin ana fikrini anla. Sadece kelime çevirisi yapma. Görsel olarak ekranda NE GÖRECEĞİZ?
- Her sahne için tam olarak 4 adet, stok video arama motorlarına (Pexels) çok uygun İNGİLİZCE "search_queries" üret.
- Sorgular kısa (2-5 kelime) ve spesifik olmalı (örn: 'astronaut floating in space', 'brain neuron connections 4k').
- Konuya göre strateji kullan: Bilim/Uzay ise 'cinematic, render, abstract'; Tarih ise 'vintage, archive'; Motivasyon ise 'nature, climbing, success' vb. eklemeler yap.
- Tekrar hissini önlemek için birbirine aşırı benzer kelimelerden kaçın.

AŞAĞIDAKİ JSON ŞEMASINA KESİN UY:
{
  "scenes": [
    {
      "scene_index": 1,
      "scene_text": "Sahne metninin buraya birebir yazılışı (kesinlikle orijinal diliyle)",
      "scene_purpose": "hook | explanation | example | emphasis | transition | cta",
      "visual_intent": "Ekranda ne görüleceğini açıklayan 1 cümlelik Türkçe not",
      "search_queries": ["query 1", "query 2", "query 3", "query 4"]
    }
  ]
}
"""

    prompt = f"""
Konu: {topic}
Tam Metin (Okunacak Script):
"{full_script}"

Lütfen bu metni analiz et ve "Sahne Planı" JSON'unu oluştur. Sadece JSON döndür.
"""

    print("🎬 Sahne planı oluşturuluyor (AI Scene Planner)...")
    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=system_prompt + "\n" + prompt,
        config=genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.7,
        ),
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        plan = json.loads(raw)
    except Exception as e:
        print(f"⚠️ JSON ayrıştırma hatası Sahne Planı: {e}")
        # Fallback plan
        plan = {
            "scenes": [
                {
                    "scene_index": 1,
                    "scene_text": full_script,
                    "scene_purpose": "explanation",
                    "visual_intent": "Genel konu anlatımı",
                    "search_queries": [f"{topic} cinematic", f"{topic} background", "abstract satisfying loop"]
                }
            ]
        }

    # Timestamp mapping
    if word_timestamps:
        plan["scenes"] = map_timestamps_to_scenes(plan["scenes"], word_timestamps)
    else:
        # Eğer timestamp yoksa tahmini eşit sürelere böl
        total_dur = 45.0
        n = len(plan["scenes"])
        dur_per = total_dur / max(n, 1)
        for i, sc in enumerate(plan["scenes"]):
            sc["start_hint"] = i * dur_per
            sc["end_hint"] = (i + 1) * dur_per

    return plan
