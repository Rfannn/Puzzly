"""Delete generated upload/output files older than a TTL (default 1 hour).

Runs three ways:
  * opportunistically from the web app (throttled, see app.py),
  * a daemon thread for local dev,
  * or standalone as a scheduled task:  python cleanup.py
"""

import os
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TTL = int(os.environ.get("FILE_TTL_SECONDS", "3600"))
TARGET_DIRS = [
    os.path.join(BASE_DIR, "static", "uploads"),
    os.path.join(BASE_DIR, "static", "output"),
]


def sweep(max_age=None, dirs=None):
    """Delete files older than `max_age` seconds. Returns count removed."""
    if max_age is None:
        max_age = DEFAULT_TTL
    dirs = dirs or TARGET_DIRS
    now = time.time()
    removed = 0
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            path = os.path.join(d, name)
            try:
                if not os.path.isfile(path):
                    continue
                if now - os.path.getmtime(path) > max_age:
                    os.remove(path)
                    removed += 1
            except OSError:
                pass
    return removed


if __name__ == "__main__":
    n = sweep()
    print(f"Removed {n} expired file(s).")
