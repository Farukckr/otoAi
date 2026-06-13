<div align="center">

# 🤖 OtoAi - Otomatik AI Video Sistemi

*Her gün otomatik olarak Türkçe kısa videolar üretir ve YouTube Shorts'a yükler.*

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Gemini API](https://img.shields.io/badge/Google%20Gemini-AI-orange?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![Pexels API](https://img.shields.io/badge/Pexels-Video%20Assets-05A081?style=for-the-badge&logo=pexels&logoColor=white)](https://www.pexels.com/api/)
[![Edge-TTS](https://img.shields.io/badge/Edge%20TTS-Voiceover-0078D7?style=for-the-badge&logo=microsoft&logoColor=white)](https://github.com/rany2/edge-tts)
[![YouTube API](https://img.shields.io/badge/YouTube%20v3-Uploader-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://developers.google.com/youtube/v3)

</div>

---

## 🌟 Özellikler

- 🧠 **Yapay Zeka Destekli Senaryo:** Google Gemini API ile tamamen özgün içerik üretimi.
- 🎙️ **Doğal Seslendirme:** Edge-TTS ile akıcı ve ücretsiz Türkçe seslendirme (`tr-TR-AhmetNeural`, `tr-TR-EmelNeural` vb.).
- 🎞️ **Otomatik Medya Seçimi:** Pexels API ile senaryoya uygun yüksek kaliteli arka plan videoları.
- 🎬 **Video Birleştirme:** FFmpeg ile akıllı video kurgusu, altyazı entegrasyonu ve Shorts uyumlu dikey format (9:16).
- 📅 **Zamanlayıcı (Scheduler):** Her gün belirlediğiniz saatte arka planda çalışarak süreci tam otomatik hale getirir.
- 🚀 **YouTube Entegrasyonu:** Üretilen videoyu otomatik olarak YouTube Shorts olarak yayınlar.

---

## 🚀 Kurulum

### 1. Gerekli Paketleri Yükleyin
Proje dizininde terminali açın ve aşağıdaki komutu çalıştırarak Python gereksinimlerini yükleyin:
```bash
pip install -r requirements.txt
```
> **⚠️ Önemli:** Sisteminizde [FFmpeg](https://ffmpeg.org/download.html) kurulu olmalı ve sistem `PATH` değişkenine eklenmiş olmalıdır.

### 2. Ortam Değişkenlerini (Env) Ayarlayın
`.env.example` dosyasının adını `.env` olarak değiştirin veya kopyalayın:
```bash
copy .env.example .env
```
Ardından `.env` dosyasını bir metin editörüyle açıp API anahtarlarınızı ekleyin:
```env
GEMINI_API_KEY=senin_api_anahtarin
PEXELS_API_KEY=senin_api_anahtarin
```
> 💡 *Not: Seslendirme için ekstra bir API anahtarına gerek yoktur, sistem ücretsiz Microsoft Edge-TTS alt yapısını kullanmaktadır.*

---

## 🎮 Kullanım & Test

Projeyi test etmek için yükleme yapmadan sadece videoyu oluşturabilirsiniz:
```bash
# Rastgele bir konu ile video oluştur (YouTube'a yüklemez)
python main.py --no-upload

# Belirli bir konu belirterek video oluştur
python main.py --topic "Her gün elma yersen ne olur?" --no-upload
```

### ⏰ Otomatik Zamanlama (Scheduler)
Sistemi tam otomatik hale getirmek için:
```bash
python scheduler.py
```
Bu komut, uygulamayı arka planda bekletir ve her gün saat **14:00**'te otomatik olarak bir video üretip YouTube'a yükler.

---

## 📺 YouTube API Kurulumu

Oluşturulan videoların YouTube kanalınıza yüklenebilmesi için:
1. [Google Cloud Console](https://console.cloud.google.com/)'a gidin ve yeni bir proje oluşturun.
2. **YouTube Data API v3** servisini etkinleştirin.
3. OAuth 2.0 İstemci Kimlikleri oluşturun (Desktop app türünde).
4. İndirdiğiniz JSON dosyasının adını `youtube_credentials.json` yapıp proje ana dizinine koyun.
5. `main.py`'yi ilk kez `--upload` ile çalıştırdığınızda tarayıcı açılır ve hesabınıza giriş yapıp onay vermeniz istenir. Sonraki kullanımlar için token kaydedilir.

---

## 📂 Proje Mimarisi

```text
otoAi/
├── main.py                  # Ana akış kontrolörü
├── scheduler.py             # Zamanlayıcı mekanizma
├── config.py                # Konfigürasyon ve ayarlar
├── .env                     # Gizli API anahtarları
├── topics/
│   └── topic_bank.json      # Konu havuzu veritabanı
├── output/                  # Üretilen videoların kaydedildiği klasör
└── modules/                 # Çekirdek Modüller
    ├── content_ai.py        # Senaryo üretici (Gemini)
    ├── tts_engine.py        # Seslendirme (Edge-TTS)
    ├── asset_fetcher.py     # Görsel/Video arama (Pexels)
    ├── video_composer.py    # Video, ses ve altyazı montajı
    └── publishers/
        └── youtube.py       # YouTube yükleme işlemleri
```

---

## 💰 Maliyet Tablosu

| Kullanılan Hizmet | Tahmini Maliyet | Özellik |
|-------------------|-----------------|---------|
| **Gemini Flash API** | Çok düşük / Ücretsiz Tier | Senaryo üretimi |
| **Edge-TTS**      | Tamamen Ücretsiz | Yüksek kaliteli yapay zeka sesi |
| **Pexels API**    | Ücretsiz | Arka plan videoları (Aylık 20.000 limit) |

---

## ❓ Sık Sorulan Sorular (FAQ)

**Q: Oluşturulan videolar nereye kaydediliyor?**  
`output/` klasörünün içine tarih ve saat damgasıyla `.mp4` formatında kaydedilir.

**Q: Botun kullanacağı konuları nasıl belirleyebilirim?**  
`topics/topic_bank.json` dosyasını düzenleyerek kendi konu havuzunuzu oluşturabilirsiniz. Bot sırayla veya rastgele bu konuları işler.

**Q: Sesin cinsiyetini veya tonunu değiştirebilir miyim?**  
Evet! `modules/tts_engine.py` dosyasındaki `TTS_VOICE` değişkenini değiştirebilirsiniz.  
Örnek Türkçe sesler: `tr-TR-AhmetNeural` (Erkek), `tr-TR-EmelNeural` (Kadın).
