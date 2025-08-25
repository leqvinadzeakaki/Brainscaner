# Brainscanner Docker პაკეტი

ეს პაკეტი შეიცავს Docker ინფრას, რომლითაც შეგიძლია გაუშვა **Brainscaner-master** (Flask + Gunicorn) კონტეინერში.

## შეიცავს:
- `Dockerfile`
- `.dockerignore`
- `docker-compose.yml`
- `README.md` (ეს ფაილი)

> თარიღი: 2025-08-25

---

## მოთხოვნები
- Docker Engine 24+
- Docker Compose v2+
- პროექტის გვერდით უნდა იდოს საქაღალდე **`Brainscaner-master/`** სადაც არის:
  - `requirements.txt`
  - `busines.py` (შეიცავს `app = Flask(__name__)` ობიექტს)
  - `.env` (საჭირო გარემო ცვლადები)
  - `client_secret.json` (Google OAuth, თუ იყენებ)

საქაღალდეების განლაგება (მინიმუმი):
```
.
├─ Brainscaner-master/
│  ├─ requirements.txt
│  ├─ busines.py
│  ├─ .env
│  ├─ client_secret.json
│  └─ uploads/           (autoload ფაილები; შეიქმნება ავტომატურადაც)
├─ Dockerfile
├─ .dockerignore
└─ docker-compose.yml
```

---

## სწრაფი გაშვება (Compose)
```bash
docker compose up -d --build
docker compose logs -f
```

- აპი გაეშვება `http://localhost:8000`
- თუ გინდა სხვა პორტი, შეცვალე `ports` ჩანაწერი `docker-compose.yml`-ში, напр.: `"8080:8000"`.

### კონტროლი
```bash
docker compose ps
docker compose restart
docker compose down
```

---

## გარემო ცვლადები (.env მაგალითი)
`.env` ფაილი უნდა იდოს `Brainscaner-master/.env`:
```
FLASK_ENV=production
SECRET_KEY=change_me
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GEMINI_API_KEY=...
PORT=8000
```

> შენიშვნა: Dockerfile-ში დეფოლტად `PORT=8000` წერია და Gunicorn ბინდავს `0.0.0.0:8000`-ზე.

---

## OAuth/Secrets ფაილები
არ ჩააშენო იმიჯში! Compose უკვე ამაგრებს:
- `Brainscaner-master/client_secret.json:/app/client_secret.json:ro`
- `Brainscaner-master/uploads:/app/uploads`

ეს უზრუნველყოფს, რომ ატვირთვები და OAuth კონფიგი კონტეინერის restart-ის შემდეგაც შენარჩუნდეს.

---

## Healthcheck
Compose იყენებს `curl`-ს `/` მისამართზე. თუ გექნება ცალკე route:
```python
@app.get("/health")
def health():
    return {"status": "ok"}, 200
```
მაშინ `docker-compose.yml`-ში შეცვალე:
```
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  ...
```

---

## Build/Run Dockerfile-ით (Compose-ის გარეშე)
```bash
docker build -t brainscanner:latest .
docker run -it --rm   -p 8000:8000   --env-file ./Brainscaner-master/.env   -v $(pwd)/Brainscaner-master/client_secret.json:/app/client_secret.json:ro   -v $(pwd)/Brainscaner-master/uploads:/app/uploads   --name brainscanner   brainscanner:latest
```

---

## ხშირი პრობლემები
1) **`ModuleNotFoundError`** — გადაამოწმე `requirements.txt` და რომ სწორად იკოპირება Dockerfile-ში.  
2) **`ImportError: cannot import app`** — დარწმუნდი, რომ აპის entrypoint არის `busines.py` და შეიცავს `app` ობიექტს. Gunicorn ეშვება `busines:app`-ით.  
3) **Upload-ები არ ინახება** — დაარემონტე volume `uploads/` (მაგ. უფლებები/ბილიკი).  
4) **OAuth redirect-uri შეცდომები** — დაამატე სწორი redirect-uri თქვენს Google Console-ში და `.env`-ში.  
5) **პროსესის “Pending/Unhealthy” სტატუსი** — გადაამოწმე `healthcheck` და რომ route აბრუნებს 200-ს.  

---

## Production რჩევები
- დაამატე reverse-proxy (nginx, Caddy) TLS-ით და gzip-ით.
- იყენე `--workers` და `--threads` Gunicorn-ში შენი რესურსების მიხედვით (CPU/RAM).
- ლოგირების აგრეგაცია: `--access-logfile - --error-logfile -` უკვე ჩართულია Compose-ში.
- Backups: `uploads/` volume-ის რეგულარული არქივაცია.

წარმატებები! 🚀
