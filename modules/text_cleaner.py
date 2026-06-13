"""
Metin temizleme ve doğrulama modülü.
Gemini'den gelen ham metni seslendirme ve altyazı için hazırlar.
Bozuk karakterleri, yabancı kelimeleri ve kodlama hatalarını yakalar.
"""
import re
import unicodedata


# ── Türkçe karakter haritası ──────────────────────────────────────────
# AI bazen yanlış Unicode veya ASCII karakter üretir.
_CHAR_FIXES = {
    # Yaygın AI hataları
    "ğ": "ğ",  # Bazen farklı Unicode codepoint gelir
    "İ": "İ",
    "ı": "ı",
    # Bozuk encoding düzeltmeleri (Mojibake)
    "Ã¶": "ö",
    "Ã¼": "ü",
    "Ã§": "ç",
    "ÅŸ": "ş",
    "Ä±": "ı",
    "ÄŸ": "ğ",
    "Ä°": "İ",
    # Aksan/diacritic hataları
    "ö́": "ö",
    "ü̈": "ü",
    # Tipik AI yazım hataları
    "detal": "detay",
    "Detal": "Detay",
    "aktivite": "etkinlik",  # İngilizce etkisi
}

# Türkçe alfabe (geçerli karakterler)
_TURKISH_CHARS = set("abcçdefgğhıijklmnoöprsştuüvyz"
                     "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ")
_ALLOWED_CHARS = _TURKISH_CHARS | set("0123456789 .,!?;:'-\"()…%&/")

# Edge-TTS'in bozuk okuduğu bilinen kalıplar (veya AI Okunuş Yazımları)
_TTS_PROBLEM_PATTERNS = [
    (r'(?i)\bei-ay\b', 'Yapay Zeka'),    # AI'nin yapay zeka kısaltması için ürettiği fonetik yazım
    (r'(?i)\bei ay\b', 'Yapay Zeka'),
    (r'\bvs\b', 've benzeri'),
    (r'\bvb\b', 've benzeri'),
    (r'\betc\b', 've benzeri'),
    (r'\baz önce\b', 'az önce'),
    (r'\.{4,}', '...'),          # 4+ nokta → 3 nokta
    (r'\s{2,}', ' '),            # Çoklu boşluk → tek boşluk
    (r'["""„]', '"'),            # Farklı tırnak → standart
    (r'[''‛]', "'"),             # Farklı apostrof → standart
    (r'[–—]', '-'),              # Dash varyantları → standart tire
    (r'\(\s*\)', ''),            # Boş parantezler
    (r'\[\s*\]', ''),            # Boş köşeli parantezler
]


def fix_encoding(text: str) -> str:
    """Mojibake ve encoding hatalarını düzeltir."""
    for broken, fixed in _CHAR_FIXES.items():
        text = text.replace(broken, fixed)
    return text


def fix_punctuation(text: str) -> str:
    """Noktalama işaretlerini düzeltir ve TTS için optimize eder."""
    for pattern, replacement in _TTS_PROBLEM_PATTERNS:
        text = re.sub(pattern, replacement, text)

    # Noktalama öncesi boşluk temizle: "kelime ." → "kelime."
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)

    # Noktalama sonrası boşluk ekle (yoksa): "kelime.Kelime" → "kelime. Kelime"
    text = re.sub(r'([.,!?;:])([A-ZÇĞİÖŞÜa-zçğıöşü])', r'\1 \2', text)

    return text.strip()


def remove_non_turkish(text: str) -> str:
    """Türkçe dışı Unicode karakterleri (Arapça, Çince vb.) temizler."""
    cleaned = []
    for char in text:
        if char in _ALLOWED_CHARS or unicodedata.category(char).startswith('Z'):
            cleaned.append(char)
        elif unicodedata.category(char) in ('Ll', 'Lu', 'Lt'):
            # Latin harfi ama Türkçe değilse (é, ñ vb.) en yakın ASCII'ye çevir
            normalized = unicodedata.normalize('NFD', char)
            ascii_char = normalized.encode('ascii', 'ignore').decode('ascii')
            if ascii_char:
                cleaned.append(ascii_char)
        # Diğer tüm egzotik karakterleri sessizce atla

    return ''.join(cleaned)


def fix_number_reading(text: str) -> str:
    """Büyük sayıları TTS'in doğru okuyacağı formata çevirir."""
    # "1.000.000" → "1 milyon" (noktalı sayılar)
    text = re.sub(r'\b(\d{1,3})\.000\.000\.000\b', r'\1 milyar', text)
    text = re.sub(r'\b(\d{1,3})\.000\.000\b', r'\1 milyon', text)
    text = re.sub(r'\b(\d{1,3})\.000\b', r'\1 bin', text)

    # "%" → "yüzde" (TTS bazen yüzde yerine "percent" okur)
    text = re.sub(r'%\s*(\d+)', r'yüzde \1', text)
    text = re.sub(r'(\d+)\s*%', r'yüzde \1', text)

    return text


def validate_text(text: str) -> dict:
    """
    Metni analiz eder ve bir rapor döndürür.
    Returns: {"clean_text": str, "issues": list[str], "char_count": int, "is_valid": bool}
    """
    issues = []
    original_len = len(text)

    # 1. Boş metin kontrolü
    if not text or not text.strip():
        return {
            "clean_text": "",
            "issues": ["Metin boş!"],
            "char_count": 0,
            "is_valid": False,
        }

    # 2. Encoding düzeltmeleri
    text = fix_encoding(text)

    # 3. Türkçe dışı karakter temizliği
    before_clean = text
    text = remove_non_turkish(text)
    if text != before_clean:
        removed = set(before_clean) - set(text) - {' '}
        if removed:
            issues.append(f"Türkçe dışı karakterler temizlendi: {removed}")

    # 4. Noktalama düzeltmeleri
    text = fix_punctuation(text)

    # 5. Sayı formatı düzeltmeleri
    text = fix_number_reading(text)

    # 6. Uzunluk kontrolü (800 karakter hedefi, ama kırpma yapılmayacak)
    if len(text) > 800:
        issues.append(f"Metin biraz uzun: {len(text)} karakter (hedef ~800)")
        # Kullanıcının isteği üzerine artık KIRPMA YAPILMIYOR.
        # Sadece bir uyarı olarak kalıyor.

    # 7. Tekrarlayan kelime kontrolü
    words = text.split()
    for i in range(len(words) - 1):
        if words[i].lower() == words[i + 1].lower() and len(words[i]) > 2:
            issues.append(f"Tekrarlayan kelime: '{words[i]}'")

    # 8. Son temizlik
    text = re.sub(r'\s+', ' ', text).strip()

    return {
        "clean_text": text,
        "issues": issues,
        "char_count": len(text),
        "original_char_count": original_len,
        "is_valid": len(text) > 0 and len(issues) < 5,
    }


def clean_for_tts(text: str) -> str:
    """
    Ana fonksiyon: Metni TTS ve altyazı için tamamen temizler.
    Pipeline'da generate_script() sonrası, generate_speech() öncesi çağrılır.
    """
    result = validate_text(text)

    if result["issues"]:
        print(f"🔍 Metin temizleme raporu ({result['original_char_count']} → {result['char_count']} kar.):")
        for issue in result["issues"]:
            print(f"   ⚠️  {issue}")

    return result["clean_text"]
