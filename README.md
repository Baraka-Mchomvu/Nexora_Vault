# Nexora Drive (MVP)

Django file storage: accounts, folders, multi-file upload, download, rename,
trash/restore, search, private share links, 128 GB quota.

## Run locally
    python -m venv venv
    source venv/bin/activate        # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    python manage.py makemigrations drive
    python manage.py migrate
    python manage.py createsuperuser
    python manage.py runserver

Open http://127.0.0.1:8000/ and log in with the account you created. Public signup is off (ALLOW_SIGNUP in settings).

## Production notes
- Set DJANGO_SECRET_KEY, DJANGO_DEBUG=0, DJANGO_ALLOWED_HOSTS=yourdomain.com
- Use PostgreSQL, Gunicorn, Nginx with HTTPS, and `collectstatic`
- Nginx: set `client_max_body_size 500M;` to match MAX_UPLOAD_BYTES
- Back up `media/` and the database daily
- Change quotas in DEFAULT_QUOTA_BYTES (settings) or per user in admin > Profiles
