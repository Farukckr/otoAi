"""
İçerik üretici modülü.
Gemini 2.0 Flash API (ÜCRETSİZ) kullanır. Kusursuz Türkçe üretir.
"""
import json
import random
import re
from pathlib import Path
from google import genai
import config
from modules.text_cleaner import clean_for_tts


def get_random_topic() -> str:
    """Konu havuzundan rastgele bir konu seçer."""
    topic_file = config.TOPICS_DIR / "topic_bank.json"

    if topic_file.exists():
        with open(topic_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        all_topics = []
        for category in data["categories"]:
            all_topics.extend(category["topics"])

        used_file = config.TOPICS_DIR / "used_topics.json"
        used = []
        if used_file.exists():
            with open(used_file, "r", encoding="utf-8") as f:
                used = json.load(f)

        available = [t for t in all_topics if t not in used]

        if not available:
            used = []
            available = all_topics

        topic = random.choice(available)
        used.append(topic)

        with open(used_file, "w", encoding="utf-8") as f:
            json.dump(used, f, ensure_ascii=False, indent=2)

        return topic

    return generate_ai_topic()


def generate_ai_topic() -> str:
    """Gemini ile yeni bir konu üretir."""
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    
    prompt = "TikTok'ta viral olabilecek, Türkçe, merak uyandıran bir kısa video konusu öner. Sadece konu başlığını yaz. Örnek: 'Her gün havuç yersen ne olur?'"
    
    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents="Sen viral TikTok içerik konuları öneren bir uzmansın.\n\n" + prompt,
        config=genai.types.GenerateContentConfig(temperature=1.0)
    )
    return response.text.strip()


def _clean_tags(text: str) -> str:
    """[YAVAŞ], [HIZLI], *kelime* gibi tag'leri temizler ama ...'ları bırakır (TTS duraksaması için)"""
    text = re.sub(r'\[.*?\]', '', text)
    text = text.replace('*', '')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def generate_script(topic: str) -> dict:
    """
    Verilen konu için video senaryosu üretir.
    Returns: title, hook, story_parts, cta, full_script, search_keywords, hashtags
    """
    print(f"📝 Senaryo üretiliyor (Gemini): {topic}")

    system_prompt = """Sen Türkçe bilim ve teknoloji videolarını seslendiren, deneyimli bir YouTube içerik seslendirmecisisin. Görevin verilen metni doğal, akıcı ve izleyiciyi ekrana kilitleyen bir ses tonuyla seslendirmek için senaryo yazmak.

TEMEL KURALLAR:
- Robotik, düz ve monoton ses kesinlikle yasak. Her cümle bir öncekinden farklı tempo ve tonda olmalı.
- Bilimsel terimler net ve güvenli telaffuz edilmeli; kelimenin üzerinde hafif bir vurgu yapılmalı.
- Şaşırma gerektiren bilgilerde (örn. "Evren 13,8 milyar yaşında") seste hafif bir "inanılmaz değil mi?" tonu olmalı.
- Soru cümlelerinde ses tonu yükselsin, cümle bitmeden önce izleyicinin merakı çekilsin.
- Rakamlar ve istatistikler yavaş ve vurgulu okunmalı; izleyici sayıyı zihninde işleyecek kadar zaman kazanmalı.
- Her paragraf arasında 0.4–0.6 saniyelik doğal nefes duraklaması ekle (... kullan).
- Bağlaçlar (ve, ama, çünkü, oysa) hızlı geçilsin; esas bilgi taşıyan kelimeler yavaşlasın.

TON REHBERİ:
- Genel tempo: Orta-hızlı (saniyede ~3,2 kelime)
- Dramatik an: Tempo %30 yavaşlasın, perde 1 ton düşsün
- Şaşırtıcı bilgi: Ses 0,5 ton yükselsin, ardından kısa duraklama (0.3s)
- Soru cümlesi: Cümle sonuna doğru yavaşla ve perde yükselt
- Teknik terim: Öncesinde mikro-duraklama (0.15s), kelimeyi vurgulu söyle

TÜRKÇE TELAFFUZ KURALLARI:
- "AI" -> "Yapay Zeka" veya "Ei-Ay" (İngilizce okunacaksa belirt)
- Yabancı bilim insanı isimleri: orijinal telaffuzu kullan, Türkçeleştirme
- Büyük sayılar kelimeyle okunmalı: "10^9" -> "milyar"
- Kısaltmalar açık okunmalı: "NASA" -> "Nasa" (hece hece değil)

YAPI (TOPLAM MAX 60 SANİYE):
[0–3 sn] HOOK: Tek cümleyle şok, merak veya "dur bir dakika" hissi yarat. Soru veya beklenmedik bir gerçekle aç.
[3–45 sn] AÇIKLAMA: Konuyu 3–4 kısa paragrafta anlat. Her paragraf tek bir fikir.
[45–58 sn] KAPANIŞ: "İşte bu yüzden..." veya "Peki sen ne düşünüyorsun?" ile bitir.

UZUNLUK KURALI: 
- Senaryonun tamamı (HOOK + STORY + CTA) toplamda en fazla 800 karakter olmalıdır.
- Saniyede ~12 karakter okuma hızıyla tam 55-60 saniyeye denk gelir.
- Videonun sonunda İZLEYİCİYİ KANALA ABONE OLMAYA/TAKİP ETMEYE YÖNLENDİREN kapanış cümlesi (CTA) kesinlikle metnin sonuna dahil edilmelidir.

CÜMLE KURALI:
- Maksimum cümle uzunluğu: 15 kelime
- Her 2–3 cümlede bir kısa (5–7 kelimelik) güçlü cümle ekle — ritim kırar, dikkat çeker
- Parantez ve uzun virgüllü cümlelerden kaçın; bunlar seslendirilince anlaşılması güç

VURGU İŞARETLERİ (metin içinde kullan):
- *kelime* -> Bu kelimeye vurgu yap
- ... -> 0.5 saniyelik duraklama
- [YAVAŞ] ve [HIZLI] etiketleri -> tempo değişimi
- [MERAK] -> Soru tonuyla oku
"""

    prompt = f"""
Konu: "{topic}"

ÖNEMLİ KURALLAR LİSTESİ:
1. Senaryoyu kendin, yepyeni bir metin olarak YAZMALISIN.
2. Videoda "Rahatlatıcı ve Estetik" (Relaxing/Satisfying) görüntüler istiyoruz.
3. EĞER KONUDA "5 sır", "3 olay" gibi sayılar geçiyorsa KESİNLİKLE LİSTELEME YAPMA. Sadece İÇLERİNDEN EN ÇARPICI 1 TANESİNİ seç ve 58 saniye boyunca sadece o tek olayı/kişiyi derinlemesine anlat!
4. YÜZDE YÜZ TÜRKÇE VE DOĞRU KARAKTERLER: "ı, ş, ğ, ç, ö, ü" karakterlerini doğru ve eksiksiz kullanmalısın.
5. MAX 60 SANİYE: Tüm metin ortalama 800 karakter civarında olmalıdır.
6. SEMANTİK EŞLEŞME: `search_keywords` listesi tam olarak 5 elemanlı olmalı. İlk kelime `hook`, sonraki 3'ü `story_parts` ve sonuncusu `cta` ile %100 uyumlu İngilizce arama terimleri olmalıdır.

Yukarıdaki rehbere sadık kalarak, aşağıdaki JSON formatını doldur:

{{
  "title": "<Buraya ilgi çekici bir başlık yaz>",
  "hook": "<Buraya izleyiciyi şok edecek, konuya giren ilk cümleni yaz (Asla liste olduğunu söyleme)>",
  "story_parts": [
    "<Buraya konunun girişini ve seçtiğin tek olayın detayını anlatan paragrafını yaz>",
    "<Buraya O TEK OLAYDAKİ en çarpıcı ve gizemli detayı anlatan paragrafını yaz>",
    "<Buraya O TEK OLAYIN sonucunu anlatan paragrafını yaz>"
  ],
  "cta": "Her gün yeni bir keşifte buluşmak için kanalımızı takip edin.",
  "full_script_with_tags": "<Buraya yukarıda yazdığın kendi metinlerini (hook + story + cta) tek parça halinde birleştir. Ve metnin içine nefes için ... ve tempo için [YAVAŞ], *vurgu* etiketlerini serpiştir. LÜTFEN TALİMATLARI OKUMA, KENDİ YAZDIĞIN HİKAYEYİ BURAYA VER!>",
  "youtube_description": "<Bu videonun konusu hakkında ek bilgiler veren, okuması keyifli, SEO uyumlu, izleyicide merak uyandıran 1-2 paragraflık şık bir Youtube Video açıklaması yaz. (Videonun birebir transkripti olmasın, konuyla ilgili minik bir blog yazısı/özet gibi olsun)>",
  "instagram_caption": "<Instagram Reels için bol emojili, merak uyandıran, kısa ve öz, etkileşim (kaydetme/paylaşma) odaklı bir açıklama yaz. Örn: 'Bunu biliyor muydun? 😱 Sonuna kadar izle! 👇'>",
  "search_keywords": ["hook keyword", "part 1 keyword", "part 2 keyword", "part 3 keyword", "cta keyword"],
  "hashtags": ["#türkçe", "#bilgi", "#viral", "#konu1"]
}}

Sadece JSON döndür, başka hiçbir şey ekleme.
"""

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    
    combined_prompt = system_prompt + "\n\n" + prompt
    
    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=combined_prompt,
        config=genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.8,
        ),
    )

    raw = response.text.strip()

    # Kod bloğu sarmalı varsa temizle
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    result = json.loads(raw)
    result["topic"] = topic
    
    # Kelimeleri garanti altına al
    enhanced_keywords = []
    for k in result.get("search_keywords", []):
        k_lower = k.lower()
        if not any(x in k_lower for x in ["relax", "nature", "satisfy", "cinematic", "peaceful", "abstract", "4k"]):
            enhanced_keywords.append(f"{k} satisfying loop")
        else:
            enhanced_keywords.append(k)
    
    # Pexels araması için garanti kelimeler
    if len(enhanced_keywords) < 5:
        enhanced_keywords.extend(["relaxing 4k nature", "peaceful mountain drone", "satisfying sand loop"])
        
    result["search_keywords"] = enhanced_keywords
    
    # Temiz metni full_script olarak kaydet
    tagged_script = result.get("full_script_with_tags", "")
    if not tagged_script:
        tagged_script = result.get("full_script", "")
    result["full_script"] = clean_for_tts(_clean_tags(tagged_script))

    print(f"✅ Senaryo hazır: {result['title']}")
    return result

