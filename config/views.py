import os
import uuid

from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view

from .models import StorageApp, StoredFile
from .utils import resolve_category, get_file_extension



def _master_auth(request) -> bool:
    return request.headers.get("X-Master-Key") == settings.STORAGE_MASTER_KEY


def _app_auth(request):
    """Returns StorageApp or None."""
    token = request.headers.get("X-App-Token")
    app_name = request.headers.get("X-App-Name")
    if not token or not app_name:
        return None
    try:
        return StorageApp.objects.get(name=app_name, token=token, is_active=True)
    except StorageApp.DoesNotExist:
        return None


def _allowed_origin(request) -> bool:
    origin = request.headers.get("Origin")
    return not origin or origin in settings.ALLOWED_SERVER_ORIGINS


def _file_url(relative_path: str, request=None) -> str:
    """Build an absolute public URL for a stored file."""
    base = settings.MEDIA_URL.rstrip("/")
    return f"{base}/{relative_path}"



@api_view(["POST"])
def register_app(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    name = request.data.get("name", "").strip()
    if not name:
        return JsonResponse({"error": "name is required"}, status=400)

    if StorageApp.objects.filter(name=name).exists():
        return JsonResponse({"error": "App already exists"}, status=409)

    app = StorageApp.objects.create(name=name)
    app.generate_token()

    return JsonResponse({"app": app.name, "token": app.token}, status=201)


@api_view(["POST"])
def revoke_token(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    name = request.data.get("name", "").strip()
    try:
        app = StorageApp.objects.get(name=name)
    except StorageApp.DoesNotExist:
        return JsonResponse({"error": "App not found"}, status=404)

    app.generate_token()
    return JsonResponse({"app": app.name, "token": app.token})


@api_view(["PATCH"])
def toggle_app(request):
    """Activate or deactivate an app without deleting it."""
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    name = request.data.get("name", "").strip()
    try:
        app = StorageApp.objects.get(name=name)
    except StorageApp.DoesNotExist:
        return JsonResponse({"error": "App not found"}, status=404)

    app.is_active = not app.is_active
    app.save(update_fields=["is_active"])
    return JsonResponse({"app": app.name, "is_active": app.is_active})



@api_view(["POST"])
def upload_file(request):
    if not _allowed_origin(request):
        return JsonResponse({"error": "Origin not allowed"}, status=403)

    app = _app_auth(request)
    if app is None:
        return JsonResponse({"error": "Invalid or missing credentials"}, status=403)

    file_obj = request.FILES.get("file")
    if not file_obj:
        return JsonResponse({"error": "No file provided"}, status=400)

    mime_type = file_obj.content_type or ""
    category = resolve_category(mime_type)
    ext = get_file_extension(file_obj.name)

    stored_name = f"{uuid.uuid4().hex}.{ext}"
    relative_path = f"{app.name}/{category}/{stored_name}"
    abs_dir = os.path.join(settings.MEDIA_ROOT, app.name, category)
    abs_path = os.path.join(abs_dir, stored_name)

    os.makedirs(abs_dir, exist_ok=True)

    with open(abs_path, "wb+") as dest:
        for chunk in file_obj.chunks():
            dest.write(chunk)

    record = StoredFile.objects.create(
        app=app,
        original_name=file_obj.name,
        stored_name=stored_name,
        category=category,
        mime_type=mime_type,
        size_bytes=file_obj.size,
        relative_path=relative_path,
    )

    return JsonResponse({
        "id": record.id,
        "url": _file_url(relative_path),
        "category": category,
        "mime_type": mime_type,
        "size_bytes": file_obj.size,
        "original_name": file_obj.name,
    }, status=201)



@api_view(["DELETE"])
def delete_file(request, file_id):
    if not _allowed_origin(request):
        return JsonResponse({"error": "Origin not allowed"}, status=403)

    app = _app_auth(request)
    if app is None:
        return JsonResponse({"error": "Invalid or missing credentials"}, status=403)

    try:
        record = StoredFile.objects.get(id=file_id, app=app, is_deleted=False)
    except StoredFile.DoesNotExist:
        return JsonResponse({"error": "File not found"}, status=404)

    abs_path = os.path.join(settings.MEDIA_ROOT, record.relative_path)
    if os.path.exists(abs_path):
        os.remove(abs_path)

    record.is_deleted = True
    record.save(update_fields=["is_deleted"])

    return JsonResponse({"deleted": True, "id": file_id})


@api_view(["GET"])
def list_files(request):
    app = _app_auth(request)
    if app is None:
        return JsonResponse({"error": "Invalid or missing credentials"}, status=403)

    category = request.GET.get("category")  
    qs = StoredFile.objects.filter(app=app, is_deleted=False)
    if category:
        qs = qs.filter(category=category)

    files = [
        {
            "id": f.id,
            "url": _file_url(f.relative_path),
            "original_name": f.original_name,
            "category": f.category,
            "mime_type": f.mime_type,
            "size_bytes": f.size_bytes,
            "uploaded_at": f.uploaded_at.isoformat(),
        }
        for f in qs
    ]

    return JsonResponse({"count": len(files), "files": files})