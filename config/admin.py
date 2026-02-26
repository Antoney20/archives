from django.contrib import admin
from .models import StorageApp, StoredFile


@admin.register(StorageApp)
class StorageAppAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "created_at"]
    list_filter = ["is_active"]
    readonly_fields = ["token", "created_at"]
    actions = ["generate_new_token"]

    def generate_new_token(self, request, queryset):
        for app in queryset:
            app.generate_token()
        self.message_user(request, "Tokens regenerated.")
    generate_new_token.short_description = "Regenerate token"


@admin.register(StoredFile)
class StoredFileAdmin(admin.ModelAdmin):
    list_display = ["original_name", "app", "category", "size_bytes", "uploaded_at", "is_deleted"]
    list_filter = ["app", "category", "is_deleted"]
    readonly_fields = ["app", "original_name", "stored_name", "category", "mime_type", "size_bytes", "relative_path", "uploaded_at"]
    search_fields = ["original_name", "app__name"]