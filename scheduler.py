"""
Günlük video üretim zamanlayıcısı.
Belirlenen saatte otomatik olarak video üretip yayınlar.
"""
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

import config
from main import run_daily_pipeline

# Kaçta yayınlansın? (Türkiye saati için ideal: öğleden sonra)
PUBLISH_HOUR = 14   # 14:00 (saat 2 öğleden sonra)
PUBLISH_MINUTE = 0

def main():
    scheduler = BlockingScheduler(timezone="Europe/Istanbul")
    
    # Her gün belirlenen saatte çalış
    trigger = CronTrigger(
        hour=PUBLISH_HOUR,
        minute=PUBLISH_MINUTE,
        timezone="Europe/Istanbul"
    )
    
    scheduler.add_job(
        run_daily_pipeline,
        trigger=trigger,
        id="daily_video",
        name="Günlük Video Üretimi",
        max_instances=1,
        coalesce=True
    )
    
    print("="*60)
    print("⏰ Otomatik Video Sistemi Başlatıldı!")
    print("="*60)
    print(f"  Her gün saat {PUBLISH_HOUR:02d}:{PUBLISH_MINUTE:02d}'de video üretilecek")
    print(f"  Kanal dili: {config.LANGUAGE}")
    print(f"  Günlük video sayısı: {config.VIDEOS_PER_DAY}")
    print(f"\n  Şimdi test etmek için: python main.py --no-upload")
    print(f"  Durdurmak için: Ctrl+C")
    print("="*60)
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n⛔ Zamanlayıcı durduruldu.")


if __name__ == "__main__":
    main()
