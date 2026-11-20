# ঢাকা হোম শিফটিং (Dhaka Home Shifting)

বাসা ভাড়া, শিফটিং, পুরনো জিনিস কেনাবেচা/দান এবং ক্লিনিং — এক প্ল্যাটফর্মে। VRCT প্রজেক্ট।

**এই ভার্সন (MVP) পুরোপুরি কাজ করে:** সাইন-আপ ও ইমেইল OTP (লগইনে শুধু নতুন ডিভাইসে OTP), বাসা ভাড়া (পুরো ফ্ল্যাট ও সাবলেট), ডায়মন্ড ওয়ালেট ও বিকাশ/নগদ TrxID রিচার্জ, ১ ডায়মন্ডে আনলক, লাইভ চ্যাট, রিপোর্ট ও রিফান্ড, রিভিউ, KYC (প্রাইভেট ডকুমেন্ট), নোটিফিকেশন, অ্যাডমিন প্যানেল, বাংলা/ইংরেজি।
শিফটিং, কেনাবেচা/দান ও ক্লিনিং পরের ধাপে — আনলক/রিপোর্ট/রিফান্ড ইঞ্জিন সেগুলোর জন্য আগেই তৈরি (`backend/app/services/listings.py`)।

| অংশ | টেকনোলজি |
|---|---|
| Backend | FastAPI, SQLAlchemy 2 (async), MySQL 8 / SQLite (টেস্ট), Alembic, WebSocket |
| Frontend | Next.js 14 (App Router), Tailwind CSS, next-intl (বাংলা/English) |
| ফাইল | Cloudinary (KYC ডকুমেন্ট `authenticated` — প্রাইভেট) |
| ইমেইল | Brevo HTTP API (প্রোডাকশন), Gmail SMTP (ঐচ্ছিক, লোকাল) |

## লোকাল কম্পিউটারে চালানো

দরকার: Python 3.11+ এবং Node.js 20+।

```bash
# 1) Backend
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head          # টেবিল তৈরি
python -m scripts.seed        # ঢাকার এলাকা ও ডিফল্ট সেটিংস
python -m scripts.create_admin --name "Admin" --email you@example.com --phone 01XXXXXXXXX
uvicorn app.main:app --reload --port 8000
```

`BREVO_API_KEY` ও `SMTP_USER` খালি থাকলে OTP কোড ইমেইলে না গিয়ে **backend-এর টার্মিনালে** দেখা যাবে।
API ডকুমেন্টেশন: http://localhost:8000/docs

```bash
# 2) Frontend (নতুন টার্মিনালে)
cd frontend
npm install
cp .env.example .env.local
npm run dev                   # http://localhost:3000
```

```bash
# টেস্ট
cd backend && python -m pytest -q
```

## অনলাইনে তোলা (ফ্রি টিয়ার)

1. **ডাটাবেস — Aiven MySQL বা TiDB Cloud Serverless:** একটি ফ্রি MySQL বানিয়ে কানেকশন তথ্য নিন।
   `DATABASE_URL=mysql+aiomysql://USER:PASS@HOST:PORT/DB?charset=utf8mb4`
   (TiDB/Aiven-এ SSL লাগলে তাদের ডকুমেন্টেশন অনুযায়ী `ssl` প্যারামিটার যোগ করুন।)
2. **Backend — Render (Free Web Service):**
   - Root directory: `backend`
   - Build: `pip install -r requirements.txt`
   - Start: `alembic upgrade head && python -m scripts.seed && uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"`
   - Environment: `.env.example`-এর সব ভ্যারিয়েবল; `ENVIRONMENT=production`, `COOKIE_SECURE=true`, `CORS_ORIGINS` ও `FRONTEND_URL` = Vercel ঠিকানা, `PUBLIC_BASE_URL` = Render ঠিকানা।
   - ইমেইল: Render-এর ফ্রি প্ল্যানে SMTP পোর্ট বন্ধ, তাই Gmail SMTP কাজ করবে না। Brevo-র ফ্রি অ্যাকাউন্টে `EMAIL_FROM` ঠিকানাটা Sender হিসেবে ভেরিফাই করে API key নিন, তারপর `BREVO_API_KEY` বসান।
   - প্রথম অ্যাডমিন: Render Shell থেকে `python -m scripts.create_admin ...`
3. **Frontend — Vercel:** Root directory `frontend`; Environment: `API_URL=https://<render-app>.onrender.com`, `NEXT_PUBLIC_WS_URL=wss://<render-app>.onrender.com`।
4. **শিডিউলড জব — GitHub Actions:** রিপোর Settings → Secrets-এ `API_URL` ও `JOB_SECRET` দিন। `.github/workflows/jobs.yml` প্রতি ঘণ্টায় মেয়াদোত্তীর্ণ পোস্ট বন্ধ করবে।

**জানা সীমাবদ্ধতা:**
- Render ফ্রি সার্ভার ১৫ মিনিট কেউ না এলে ঘুমিয়ে যায় — প্রথম রিকোয়েস্টে ~১ মিনিট লাগতে পারে। চ্যাট নিজে থেকে আবার কানেক্ট হয় এবং মেসেজ হারায় না। প্রেজেন্টেশনের আগে সাইট একবার খুলে রাখুন।
- Vercel Hobby প্ল্যান অ-বাণিজ্যিক ব্যবহারের জন্য — প্রজেক্ট/ডেমোর জন্য ঠিক আছে।
- বিকাশ/নগদ রিচার্জ ম্যানুয়াল (অ্যাডমিন TrxID মিলিয়ে অ্যাপ্রুভ করেন)। পেমেন্ট গেটওয়ে পরের ধাপে।

## ফোল্ডার

```
backend/
  app/core/        কনফিগ, ডাটাবেস, নিরাপত্তা, দ্বিভাষিক এরর
  app/models.py    সব টেবিল
  app/routers/     auth, rent, trust (আনলক/রিপোর্ট/রিভিউ), wallet, chat, account (KYC/নোটিফিকেশন), admin, internal
  app/services/    ওয়ালেট লেজার, OTP, ইমেইল, ফাইল, কন্টাক্ট ফিল্টার, রিফান্ড
  alembic/         ডাটাবেস মাইগ্রেশন
  scripts/         seed, create_admin
  tests/           pytest
frontend/
  app/             পেজ (হোম, লগইন, বাসা, পোস্ট, ওয়ালেট, মেসেজ, ড্যাশবোর্ড, KYC, অ্যাডমিন)
  messages/        bn.json, en.json — সব লেখা
  components/, lib/
```
