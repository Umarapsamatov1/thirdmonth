from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('courses/', views.courses, name='courses'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('languages/', views.languages, name='languages'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('register/', views.register, name='register'),
    path("newsletter/", views.newsletter_subscribe, name="newsletter"),
]
