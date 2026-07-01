# بورس اینسایت — Bourse Insight

سامانه هوشمند جستجوی لحظه‌ای اطلاعات مالی شرکت‌های بورس ایران

## ویژگی‌ها

- **جستجوی زنده از Codal.ir** — بدون نیاز به ثبت‌نام، مستقیماً از سامانه کدال داده دریافت می‌شود
- **بای‌پس TLS Fingerprint** — استفاده از `curl` سیستمی برای دور زدن محدودیت‌های سایت‌های ایرانی
- **کش حافظه‌ای ۲ ساعته** — درخواست‌های تکراری بدون نیاز به درخواست مجدد از سرور
- **پشتیبانی از هر نمادی** — فقط نمادهای ثبت شده در دیتابیس نیست، هر نمادی در Codal.ir جستجو می‌شود
- **API RESTful** — دسترسی به داده‌ها از طریق API
- **رابط کاربری تاریک** — تم نئونی با فونت وزیرمتن

## معماری سیستم

```
┌──────────┐     ┌──────────────┐     ┌───────────────┐     ┌────────────┐
│  Browser  │────>│  Django Web  │────>│  CodalService  │────>│  Codal.ir  │
│  (HTML)   │<────│  (Views)     │<────│  (Scraper)     │<────│  (API/XML) │
└──────────┘     └──────┬───────┘     └───────┬───────┘     └────────────┘
                        │                      │
                   ┌────┴────┐           ┌─────┴─────┐
                   │  SQLite  │           │ In-Memory │
                   │  (Companies/│        │  Cache    │
                   │   Sectors)  │        │  (2h TTL) │
                   └──────────┘           └───────────┘
```

## راه‌اندازی

```bash
cd bourse-insight
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py shell < scripts/seed_data.py
python manage.py runserver 0.0.0.0:8000
```

## API Endpoints

| Endpoint | توضیح |
|----------|-------|
| `GET /api/v1/search-codal/?q=فولاد` | جستجوی گزارشات از Codal.ir |
| `GET /api/v1/search-codal/<symbol>/all/` | دریافت تمام صفحات |
| `GET /api/v1/companies/<symbol>/reports/` | گزارشات با اطلاعات شرکت |
| `GET /api/v1/autocomplete/?term=فولاد` | تکمیل خودکار |
| `GET /api/v1/sectors/` | لیست صنایع |
| `GET /api/v1/search/companies/?q=فولاد` | جستجوی شرکت‌ها در DB |
| `GET /api/v1/debug-codal/?q=فولاد` | دیباگ پاسخ Codal |

## تکنولوژی‌ها

- Django 6 + Python 3.12
- SQLite + Prisma-style ORM
- Bootstrap 5.3 RTL + Vazirmatn
- System curl for TLS bypass
- In-memory cache