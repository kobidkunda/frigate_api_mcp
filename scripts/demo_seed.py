import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datetime import datetime, timedelta, timezone
from factory_analytics.database import Database

db = Database()
cam = db.upsert_camera('demo_camera', 'Demo Camera')
db.update_camera(cam['id'], {'enabled': 1, 'interval_seconds': 300})
for i, label in enumerate(['working', 'idle', 'sleeping', 'working', 'idle']):
    job = db.schedule_job(cam['id'], payload={'source': 'seed'})
    db.mark_job_running(job['id'])
    end_dt = datetime.now(timezone.utc) - timedelta(days=4-i)
    start_dt = end_dt - timedelta(minutes=5)
    db.create_segment(job['id'], cam['id'], start_dt.isoformat(), end_dt.isoformat(), label, 0.75, 'seed data')
    db.update_daily_rollup(start_dt.date().isoformat(), cam['id'], label, 300)
    db.mark_job_finished(job['id'], 'success', raw_result={'label': label, 'confidence': 0.75})
print('Seeded demo data')
