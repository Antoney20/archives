from django.db import models
import secrets


class StorageApp(models.Model):
    name = models.CharField(max_length=100, unique=True)
    token = models.CharField(max_length=128, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_token(self):
        self.token = secrets.token_urlsafe(48)
        self.save()

    def __str__(self):
        return f"{self.name} ({'active' if self.is_active else 'inactive'})"


class StoredFile(models.Model):
    """Tracks uploaded files for management, deletion, and auditing."""

    class FileCategory(models.TextChoices):
        IMAGE = "images", "Image"
        DOCUMENT = "documents", "Document"
        TEXT = "text", "Text"
        OTHER = "other", "Other"

    app = models.ForeignKey(StorageApp, on_delete=models.CASCADE, related_name="files")
    original_name = models.CharField(max_length=255)
    stored_name = models.CharField(max_length=255) 
    category = models.CharField(max_length=20, choices=FileCategory.choices)
    mime_type = models.CharField(max_length=100, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    relative_path = models.CharField(max_length=512)  
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.app.name}/{self.relative_path}"