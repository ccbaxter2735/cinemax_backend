#!/usr/bin/env bash
# test resolution pb
# exit si il y a une erreur
set -o errexit

# Installer les dépendances
pip install -r requirements.txt

python manage.py makemigrations

# Appliquer les migrations (doit être fait avant la création du superuser)
python manage.py migrate --noinput

# Collecter les fichiers statiques
python manage.py collectstatic --no-input

# Création optionnelle du superuser si CREATE_SUPERUSER est défini et non vide
# (Assure-toi d'avoir défini DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD dans les env vars Render)
if [ -n "${CREATE_SUPERUSER:-}" ]; then
  : "${DJANGO_SUPERUSER_USERNAME:?Need DJANGO_SUPERUSER_USERNAME}"
  : "${DJANGO_SUPERUSER_EMAIL:?Need DJANGO_SUPERUSER_EMAIL}"
  : "${DJANGO_SUPERUSER_PASSWORD:?Need DJANGO_SUPERUSER_PASSWORD}"

  python - <<'PY'
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.environ.get("DJANGO_SETTINGS_MODULE", "backend.deployment_settings"))
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

username = os.environ['DJANGO_SUPERUSER_USERNAME']
email = os.environ['DJANGO_SUPERUSER_EMAIL']
password = os.environ['DJANGO_SUPERUSER_PASSWORD']

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print("Superuser créé:", username)
else:
    print("Superuser existe déjà:", username)
PY
fi