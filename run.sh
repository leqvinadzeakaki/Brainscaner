#!/bin/bash
set -e

# გამოიყენე პლატფორმის PORT თუ გადმოგვცეს, ან 8080 ნაგულისხმებად
PORT=${PORT:-8080}
echo "Starting on port $PORT"

# სურვილისამებრ: requirements ინსტალაცია სტარტზეც
if [ -f requirements.txt ]; then
  pip install --upgrade pip
  pip install -r requirements.txt || true
fi

# ცნობილ entrypoint-ებზე ცდა, უკვე PORT-ით
if [ -f app.py ]; then
  exec gunicorn --bind 0.0.0.0:${PORT} app:app
fi

if [ -f wsgi.py ]; then
  exec gunicorn --bind 0.0.0.0:${PORT} wsgi:app
fi

if [ -f main.py ]; then
  exec python main.py
fi

if [ -f manage.py ]; then
  export FLASK_APP=manage.py
  exec flask run --host=0.0.0.0 --port=${PORT}
fi

# ავტო-აღმოჩენა (ჩვენს პროექტში მთავარია busines.py → app)
APP_CANDID=$(grep -R --line-number -E "Flask\(" --include=*.py . | head -n1 | cut -d: -f1 || true)
if [ -n "$APP_CANDID" ]; then
  MODULE=$(basename "$APP_CANDID" .py)
  exec gunicorn --bind 0.0.0.0:${PORT} "$MODULE":app
fi

# ფოლბექი
python -m http.server ${PORT} --bind 0.0.0.0
