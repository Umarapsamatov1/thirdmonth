from django.contrib import admin
from .models import *

admin.site.site_header = 'StudyFlow boshqaruv paneli'
admin.site.site_title = 'StudyFlow Admin'
admin.site.index_title = 'Boshqaruv markazi'


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "email",
        "discount",
        "promo_code",
        "email_sent",
        "created_at",
        "sent_at",
    )

    list_filter = ("email_sent", "created_at")
    search_fields = ("email", "promo_code")
    readonly_fields = ("email_sent", "created_at", "sent_at")
    list_per_page = 20


admin.site.register(StudentProfile)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "subject",
        "is_read",
        "created_at",
    )
    list_filter = (
        "is_read",
        "created_at",
    )
    search_fields = (
        "name",
        "email",
        "subject",
    )
    list_editable = ("is_read",)
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

