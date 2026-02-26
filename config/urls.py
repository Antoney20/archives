from django.contrib import admin
from django.urls import path

from config import views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("upload/", views.upload_file, name="upload_file"),
    path("register-app/", views.register_app, name="register_app"),
    path("revoke-token/", views.revoke_token, name="revoke_token"),
]