from django import template
from django.apps import apps
from django.contrib.auth import get_user_model
from django.urls import NoReverseMatch, reverse

from core.models import Contact, Newsletter, StudentProfile

register = template.Library()

# Admin bo‘limlari uchun saytdagi kabinet uslubidagi belgilar.
MODEL_ICONS = {
    "auth.user": "👥",
    "auth.group": "🛡️",
    "core.newsletter": "✉️",
    "core.studentprofile": "🎓",
    "core.contact": "💬",
}
ROLES = {
    "super": {
        "key": "super",
        "label": "Super admin",
        "text": "Platformaning barcha bo‘limlari, foydalanuvchilar va ruxsatlar ustidan to‘liq nazorat sizda.",
    },
    "staff": {
        "key": "staff",
        "label": "Staff admin",
        "text": "Sizga ruxsat berilgan bo‘limlar shu yerda. Qo‘shimcha huquq kerak bo‘lsa, super admin bilan bog‘laning.",
    },
}


def _changelist_url(model, query=""):
    opts = model._meta
    try:
        return reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist") + query
    except NoReverseMatch:
        return ""


def _can_view(user, model):
    opts = model._meta
    return user.has_perm(f"{opts.app_label}.view_{opts.model_name}") or user.has_perm(
        f"{opts.app_label}.change_{opts.model_name}"
    )


@register.simple_tag
def sf_model_icon(app_label, object_name):
    return MODEL_ICONS.get(f"{app_label}.{object_name}".lower(), "📁")


@register.simple_tag
def sf_model_count(app_label, object_name):
    try:
        return apps.get_model(app_label, object_name)._default_manager.count()
    except LookupError:
        return 0


@register.simple_tag
def sf_role(user):
    return ROLES["super" if user.is_superuser else "staff"]


@register.simple_tag
def sf_display_name(user):
    name = user.get_short_name() or user.get_username()
    return name.split("@")[0]


@register.simple_tag
def sf_unread_contacts(user):
    if not _can_view(user, Contact):
        return None
    return Contact.objects.filter(is_read=False).count()


@register.simple_tag
def sf_admin_stats(user):
    """Bosh sahifadagi metrika kartalari — faqat foydalanuvchi ko‘ra oladigan bo‘limlar."""
    User = get_user_model()
    cards = []

    if _can_view(user, User):
        staff = User.objects.filter(is_staff=True).count()
        cards.append({
            "label": "Foydalanuvchilar", "icon": "👥", "tone": "blue",
            "value": User.objects.count(), "hint": f"{staff} ta admin va staff",
            "url": _changelist_url(User),
        })
    if _can_view(user, StudentProfile):
        cards.append({
            "label": "Talabalar", "icon": "🎓", "tone": "",
            "value": StudentProfile.objects.count(), "hint": "Ro‘yxatdan o‘tgan talabalar",
            "url": _changelist_url(StudentProfile),
        })
    if _can_view(user, Newsletter):
        sent = Newsletter.objects.filter(email_sent=True).count()
        cards.append({
            "label": "Obunachilar", "icon": "✉️", "tone": "lime",
            "value": Newsletter.objects.count(), "hint": f"{sent} tasiga chegirma yuborilgan",
            "url": _changelist_url(Newsletter),
        })
    if _can_view(user, Contact):
        unread = Contact.objects.filter(is_read=False).count()
        cards.append({
            "label": "Xabarlar", "icon": "💬", "tone": "dark",
            "value": Contact.objects.count(), "hint": f"{unread} ta o‘qilmagan",
            "url": _changelist_url(Contact, "?is_read__exact=0" if unread else ""),
        })
    return cards
