# Backend Setup

This backend uses environment variables stored in `frontend_backend/backend/.env`.

## Setup

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` and set your production values.

3. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```

## Required Environment Variables

The backend expects these values to be present in `.env`:

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`
- `CSRF_TRUSTED_ORIGINS`
- `DB_ENGINE`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`

## Notes

- `DEBUG` must be `True` or `False`.
- Comma-separated values are supported for `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, and `CSRF_TRUSTED_ORIGINS`.
- The backend will fail to start if any required environment variable is missing.
