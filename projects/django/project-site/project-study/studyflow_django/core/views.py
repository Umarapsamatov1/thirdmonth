from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout, get_user_model

from django.shortcuts import render

import smtplib

from django.shortcuts import redirect
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import *
from .forms import *


def home(request): return render(request, 'index.html')


def about(request): return render(request, 'about.html')


def courses(request): return render(request, 'courses.html')


def languages(request): return render(request, 'languages.html')


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Xabaringiz muvofaqiyatli yuborildi!"
            )
            return redirect("contact")

        messages.error(
            request,
            "Ma'lumotlarni tog'ri kiriting!"
        )
    return render(request, 'contact.html')


@login_required(login_url="login")
def dashboard(request):
    return render(request, "dashboard.html")


@require_http_methods(["GET", "POST"])
def login(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]
        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        account = authenticate(
            request, username=user.get_username(), password=password
        ) if user else None

        if account is not None:
            auth_login(request, account)
            return redirect("dashboard")
        form.add_error(None, "Email yoki parol noto‘g‘ri.")

    return render(request, "login.html", {"form": form})


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        User = get_user_model()
        name = form.cleaned_data["name"]
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]
        # Unique username=email for Django's built-in User model.
        user = User.objects.create_user(
            username=email, email=email, password=password, first_name=name
        )
        StudentProfile.objects.get_or_create(user=user)
        auth_login(request, user)
        return redirect("dashboard")

    return render(request, "register.html", {"form": form})


@require_POST
def logout(request):
    auth_logout(request)
    return redirect("home")


@require_POST
def newsletter_subscribe(request):
    email = request.POST.get("email", "").strip().lower()

    # Emailni tekshirish
    try:
        validate_email(email)
    except ValidationError:
        messages.error(request, "Email manzil noto'g'ri!")
        return redirect("/")

    # Foydalanuvchini bazaga qo'shish
    newsletter, created = Newsletter.objects.get_or_create(
        email=email
    )

    # Oldin email yuborilgan bo'lsa
    if newsletter.email_sent:
        messages.info(
            request,
            "Sizga chegirma xati avval yuborilgan!"
        )
        return redirect("/")

    # Email uchun matn
    subject = "StudyFlow | Siz 30% chegirmaga ega bo'ldingiz!"

    message = f"""
Tabriklaymiz!

Siz StudyFlow kurslari uchun {newsletter.discount}% chegirmaga ega bo'ldingiz!

Sizning promo-kodingiz: {newsletter.promo_code}

Bizni tanlaganingiz uchun rahmat!

Hurmat bilan,
StudyFlow jamoasi
"""

    # Chiroyli HTML email
    html_message = render_to_string(
        "emails/discount.html",
        {
            "discount": newsletter.discount,
            "promo_code": newsletter.promo_code,
        }
    )

    try:
        result = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )

        if result == 1:
            newsletter.email_sent = True
            newsletter.sent_at = timezone.now()
            newsletter.save(
                update_fields=["email_sent", "sent_at"]
            )

            messages.success(
                request,
                "Tabriklaymiz! 30% chegirma emailingizga yuborildi!"
            )
        else:
            messages.error(
                request,
                "Email yuborilmadi. Qayta urinib ko'ring."
            )

    except (smtplib.SMTPException, OSError):
        messages.error(
            request,
            "Email yuborishda xatolik. Keyinroq qayta urinib ko'ring."
        )

    return redirect("/")
