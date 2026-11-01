# StudyFlow Django — Login / Register tuzatilgan

## Ishga tushirish

Windows PowerShell yoki terminal:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

- http://127.0.0.1:8000/register/ — yangi akkaunt
- http://127.0.0.1:8000/login/ — email va parol bilan kirish
- http://127.0.0.1:8000/dashboard/ — faqat login qilganlar uchun
- Chiqish barcha sahifalarda POST forma + CSRF bilan ishlaydi.

`models.py`: Django User + StudentProfile + Newsletter saqlandi.
`core/forms.py`: login/register validatsiyasi.
`core/views.py`: Django auth autentifikatsiyasi.
`templates/login.html`, `register.html`, `dashboard.html`: backend bilan ulangan.
`static/assets/js/app.js`: localStorage-demo auth olib tashlangan.

Oldingi `db.sqlite3` fayli saqlandi (mavjud ma'lumotlar o'chirilmaydi).

## Email / newsletter

Mahalliy rivojlantirishda `EMAIL_HOST_USER` va `EMAIL_HOST_PASSWORD` kiritilmasa xatlar terminalga chiqariladi.
Haqiqiy Gmail SMTP uchun environment variable sozlang:

```powershell
$env:EMAIL_HOST_USER="your_email@gmail.com"
$env:EMAIL_HOST_PASSWORD="your_new_app_password"
```

**Muhim:** asl ZIP ichidagi Gmail app-password ochiq ko‘rinishda bo‘lgan. Uni Google akkaunt xavfsizlik sozlamalaridan darhol bekor qiling va yangisini yarating.

Productiondan oldin `DJANGO_SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, SSL va parol validatorlarini moslang. `venv` va IDE fayllari arxivga kiritilmagan — loyihaning kodi va bazasi saqlangan.
