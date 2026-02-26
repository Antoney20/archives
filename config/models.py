from django.db import models
import secrets
import string

def generate_secure_token(length=20):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class StorageApp(models.Model):
    name = models.CharField(max_length=100, unique=True)
    token = models.CharField(max_length=20, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = generate_secure_token(20)

            # Ensure uniqueness
            while StorageApp.objects.filter(token=self.token).exists():
                self.token = generate_secure_token(20)

        super().save(*args, **kwargs)

    def regenerate_token(self):
        self.token = generate_secure_token(20)
        while StorageApp.objects.filter(token=self.token).exists():
            self.token = generate_secure_token(20)
        self.save(update_fields=["token"])

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