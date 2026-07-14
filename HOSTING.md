# Hosting Puzzly (e.g. PythonAnywhere)

This guide covers deploying the public demo at
**https://puzzly.pythonanywhere.com/**. Secrets stay in a git-ignored `.env`.

## One-time setup
1. Upload the project files to your host home directory.
2. Create/select a virtualenv and install dependencies:
   ```bash
   pip install -r requirements.lock.txt   # fully pinned, reproducible
   ```
3. Point the web app's source to this directory and set the WSGI file to:
   ```python
   import sys, os
   sys.path.append("/home/youruser/puzzly")
   from app import app as application
   ```
4. Reload. The app is live (debug is off, so `SECRET_KEY` is required).

## Environment variables (host `.env`, git-ignored)
```
SECRET_KEY=<generated: python -c "import secrets; print(secrets.token_hex(32))">
ADMIN_TOKEN=<generated: python -c "import secrets; print(secrets.token_urlsafe(24))">
SESSION_COOKIE_SECURE=1
FLASK_DEBUG=0
PROXY_TRUSTED=1
FILE_TTL_SECONDS=3600
```
- `SESSION_COOKIE_SECURE=1` — marks the session cookie `Secure` over HTTPS.
- `PROXY_TRUSTED=1` — the host sits behind a proxy, so this makes the app read
  the real client IP from `X-Forwarded-For` for the usage logs.
- `FLASK_DEBUG=0` is required so `SECRET_KEY` is enforced (a random dev key is
  only auto-generated in debug mode).

## Scheduled cleanup
The in-process cleanup thread is unreliable once a worker goes idle. Add a
scheduled task (e.g. hourly) that runs:

```
python /home/youruser/puzzly/cleanup.py
```

This guarantees generated uploads/outputs are deleted after their TTL even if
the web worker has been reaped (the throttled in-request sweep covers gaps).

## Default pictures
The picture library shown to users is the `library/` folder on the host
(git-ignored). Drop a few kid-friendly images there so the demo is usable
without uploading.
