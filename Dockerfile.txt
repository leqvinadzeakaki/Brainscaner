FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    FLASK_ENV=production

RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY Brainscaner-master/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY Brainscaner-master/ /app/

RUN mkdir -p /app/uploads

RUN useradd -ms /bin/bash appuser
USER appuser

EXPOSE 8000

CMD ["gunicorn", "busines:app", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "120"]
