# OtoAi - Otomatik AI Video Sistemi

Her gun otomatik olarak Turkce kisa videolar uretir ve YouTube Shorts'a yukler.

## Kurulum

### 1. Paketleri yukle
```bash
pip install -r requirements.txt
```

> Not: FFmpeg de gerekli. `ffmpeg` komutunun PATH icinde oldugundan emin ol.

### 2. Ortam degiskenlerini ayarla
`.env.example` dosyasini `.env` olarak kopyala:

```bash
copy .env.example .env
```

Sonra `.env` icini doldur:

```env
GEMINI_API_KEY=...
PEXELS_API_KEY=...
```

> Not: Seslendirme icin ayri bir API key gerekmez. Proje `edge-tts` kullanir.

### 3. Test et
```bash
python main.py --no-upload
python main.py --topic "Her gun elma yersen ne olur?" --no-upload
```

## Otomatik zamanlama

Her gun saat 14:00'te video uretip YouTube'a yuklemek icin:

```bash
python scheduler.py
```

## YouTube kurulumu

1. [Google Cloud Console](https://console.cloud.google.com/) uzerinden yeni proje olustur.
2. YouTube Data API v3'u etkinlestir.
3. OAuth2 credentials dosyasini indirip `youtube_credentials.json` olarak kaydet.
4. Ilk calistirmada tarayicida giris yapman istenecek.

## Proje yapisi

```text
otoAi/
|-- main.py
|-- scheduler.py
|-- config.py
|-- .env
|-- modules/
|   |-- content_ai.py      # Senaryo uretici (Gemini)
|   |-- tts_engine.py      # Seslendirme (Edge-TTS)
|   |-- asset_fetcher.py   # Gorsel/video (Pexels)
|   |-- video_composer.py  # Video birlestirici
|   `-- publishers/
|       `-- youtube.py
|-- topics/
|   `-- topic_bank.json
`-- output/
```

## Maliyet

| Hizmet | Maliyet |
|---|---|
| Gemini Flash (senaryo) | Kullanim miktarina gore |
| Edge-TTS (ses) | Ucretsiz |
| Pexels (gorseller) | Ucretsiz |

## Sik sorulan sorular

**Video nereye kaydedilir?**  
`output/` klasorune `.mp4` olarak yazilir.

**Kendi konumu nasil eklerim?**  
`topics/topic_bank.json` dosyasina yeni konular ekleyebilirsin.

**Farkli bir ses kullanabilir miyim?**  
`modules/tts_engine.py` icindeki `TTS_VOICE` degerini degistirebilirsin. Ornekler:
`tr-TR-AhmetNeural`, `tr-TR-EmelNeural`
