#!/bin/bash
set -e
echo "Starting auto-run helper..."

# სურვილისამებრ: სტარტზეც დააყენოს პაკეტები (თუ შეიცვალა requirements.txt)
if [ -f requirements.txt ]; then
  echo "Installing Python requirements..."
  pip install --upgrade pip
  pip install -r requirements.txt || true
fi

# პრიორიტეტით ეცდება ცნობილ ენტრიპოინტებს
if [ -f app.py ]; then
  echo "Found app.py -> trying gunicorn app:app"
  exec gunicorn --bind 0.0.0.0:8080 app:app
fi

if [ -f wsgi.py ]; then
  echo "Found wsgi.py -> trying gunicorn wsgi:app"
  exec gunicorn --bind 0.0.0.0:8080 wsgi:app
fi

if [ -f main.py ]; then
  echo "Found main.py -> trying python main.py"
  exec python main.py
fi

if [ -f manage.py ]; then
  echo "Found manage.py -> trying flask run"
  export FLASK_APP=manage.py
  exec flask run --host=0.0.0.0 --port=8080
fi

# ავტომატური აღმოჩენა: მოვძებნოთ ფაილი, სადაც ჩანს 'Flask('
APP_CANDID=$(grep -R --line-number -E "Flask\(" --include=*.py . | head -n1 | cut -d: -f1 || true)
if [ -n "$APP_CANDID" ]; then
  MODULE=$(basename "$APP_CANDID" .py)
  echo "Detected Flask app in $APP_CANDID -> trying gunicorn $MODULE:app"
  exec gunicorn --bind 0.0.0.0:8080 "$MODULE":app
fi

# ფოლბექი: უბრალოდ static სერვერი, რომ კონტეინერი მაინც გაშვდეს
echo "No known web entrypoint found. Starting a lightweight Python HTTP server on port 8080 as fallback."
python -m http.server 8080 --bind 0.0.0.0
