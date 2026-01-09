import time
import subprocess
from datetime import datetime

INTERVAL_MIN = 10

while True:
    print(f"\n[{datetime.now()}] Collecting traffic snapshot...")
    subprocess.run(["python", "collector/collect_tomtom.py"], check=False)
    print(f"[{datetime.now()}] Sleeping {INTERVAL_MIN} minutes...")
    time.sleep(INTERVAL_MIN * 60)
