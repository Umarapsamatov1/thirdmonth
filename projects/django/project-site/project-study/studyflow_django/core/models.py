from django.db import models
from django.conf import settings


class Newsletter(models.Model):
    email = models.EmailField("Email", unique=True)
    discount = models.PositiveIntegerField("Chegirma (%)", default=30)
    promo_code = models.CharField("Promo-kod", max_length=30, default="STUDY30")
    email_sent = models.BooleanField("Xat yuborilgan", default=False)
    created_at = models.DateTimeField("Obuna bo‘lgan vaqt", auto_now_add=True)
    sent_at = models.DateTimeField("Xat yuborilgan vaqt", null=True, blank=True)

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = "Obunachi"
        verbose_name_plural = "Obunachilar"
        ordering = ["-created_at"]


class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
        verbose_name="Foydalanuvchi",
    )
    created_at = models.DateTimeField("Ro‘yxatdan o‘tgan vaqt", auto_now_add=True)

    def __str__(self):
        return self.user.get_username()

    class Meta:
        verbose_name = "Talaba profili"
        verbose_name_plural = "Talaba profillari"


class Contact(models.Model):
    name = models.CharField("Ism", max_length=120)
    email = models.EmailField("Email")
    subject = models.CharField("Mavzu", max_length=200, blank=True)
    message = models.TextField("Xabar matni")
    is_read = models.BooleanField("O‘qilgan", default=False)
    created_at = models.DateTimeField("Yuborilgan vaqt", auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.email}"

    class Meta:
        verbose_name = "Xabar"
        verbose_name_plural = "Xabarlar"
        ordering = ['-created_at']





