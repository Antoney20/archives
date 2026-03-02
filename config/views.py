import os
import uuid
import re
from datetime import datetime

from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view

from .models import StorageApp, StoredFile
from .utils import resolve_category, get_file_extension

from .exceptions import *
from .responses import error_response


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
    # No Origin header = server-to-server request, always allow
    return not origin or origin in settings.ALLOWED_SERVER_ORIGINS


def _file_url(relative_path: str) -> str:
    """
    Build an absolute public URL for a stored file.
    MEDIA_URL must be set to the full public base in production,
    e.g. https://media.cema.africa/media/
    """
    base = settings.MEDIA_URL.rstrip("/")
    return f"{base}/{relative_path}"


# ------------------------------------------------------------------
# Admin endpoints (superuser only)
# ------------------------------------------------------------------

@api_view(["POST"])
def register_app(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    name = request.data.get("name", "").strip()
    if not name:
        return JsonResponse({"error": "name is required"}, status=400)

    if StorageApp.objects.filter(name=name).exists():
        return JsonResponse({"error": "App already exists"}, status=409)

    # .save() auto-generates the token, so no extra call needed
    app = StorageApp.objects.create(name=name)

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

    # FIX: was incorrectly calling app.generate_token() — method is regenerate_token()
    app.regenerate_token()
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
    try:
        # ---------------------------
        # Origin validation
        # ---------------------------
        if not _allowed_origin(request):
            raise OriginNotAllowed("Origin not allowed")

        # ---------------------------
        # App authentication
        # ---------------------------
        app = _app_auth(request)
        if app is None:
            raise AuthenticationFailed("Invalid credentials")

        # ---------------------------
        # File validation
        # ---------------------------
        file_obj = request.FILES.get("file")
        if not file_obj:
            raise FileMissing("No file provided")

        mime_type = file_obj.content_type or ""
        category = resolve_category(mime_type)
        ext = get_file_extension(file_obj.name)

        # ---------------------------
        # Sanitize app name
        # ---------------------------
        safe_app = re.sub(r"[^a-z0-9_-]", "", app.name.lower())

        # normalize filename (avoid traversal)
        base_name = re.sub(
            r"[^a-z0-9]+",
            "",
            os.path.splitext(file_obj.name)[0].lower()
        )[:12] or "file"

        # YYYYMM like cloud providers
        date_part = datetime.utcnow().strftime("%Y%m")

        # ---------------------------
        # Create DB record first (get ID)
        # ---------------------------
        record = StoredFile.objects.create(
            app=app,
            original_name=file_obj.name,
            stored_name="",
            category=category,
            mime_type=mime_type,
            size_bytes=file_obj.size,
            relative_path="",
        )

        # deterministic filename
        stored_name = f"{base_name}-{date_part}-{record.id}.{ext}"

        relative_path = f"{safe_app}/{category}/{stored_name}"
        abs_path = os.path.join(settings.MEDIA_ROOT, relative_path)

        # ---------------------------
        # Ensure directory exists
        # ---------------------------
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        # ---------------------------
        # Save file (streamed)
        # ---------------------------
        with open(abs_path, "wb+") as dest:
            for chunk in file_obj.chunks():
                dest.write(chunk)

        # ---------------------------
        # Update record
        # ---------------------------
        record.stored_name = stored_name
        record.relative_path = relative_path
        record.save(update_fields=["stored_name", "relative_path"])

        return JsonResponse(
            {
                "id": record.id,
                "url": _file_url(relative_path),
                "category": category,
                "mime_type": mime_type,
                "size_bytes": file_obj.size,
                "original_name": file_obj.name,
            },
            status=201,
        )

    except OriginNotAllowed as e:
        return JsonResponse({"error": str(e)}, status=403)

    except AuthenticationFailed as e:
        return JsonResponse({"error": str(e)}, status=403)

    except FileMissing as e:
        return JsonResponse({"error": str(e)}, status=400)

    except Exception as e:
        return JsonResponse(
            {"error": "Upload failed", "detail": str(e)},
            status=500,
        )


@api_view(["DELETE"])
def delete_file(request, file_id):
    try:
        if not _allowed_origin(request):
            raise OriginNotAllowed("Origin not allowed")

        app = _app_auth(request)
        if app is None:
            raise AuthenticationFailed("Invalid credentials")

        try:
            record = StoredFile.objects.get(
                id=file_id,
                app=app,
                is_deleted=False,
            )
        except StoredFile.DoesNotExist:
            return JsonResponse({"error": "File not found"}, status=404)

        abs_path = os.path.join(settings.MEDIA_ROOT, record.relative_path)

        # remove physical file if exists
        if os.path.exists(abs_path):
            os.remove(abs_path)

        record.is_deleted = True
        record.save(update_fields=["is_deleted"])

        return JsonResponse({"deleted": True, "id": file_id})

    except OriginNotAllowed as e:
        return JsonResponse({"error": str(e)}, status=403)

    except AuthenticationFailed as e:
        return JsonResponse({"error": str(e)}, status=403)

    except Exception as e:
        return JsonResponse(
            {"error": "Delete failed", "detail": str(e)},
            status=500,
        )

@api_view(["GET"])
def list_files(request):
    try:
        if not _allowed_origin(request):
            raise OriginNotAllowed("Origin not allowed")

        app = _app_auth(request)
        if app is None:
            raise AuthenticationFailed("Invalid credentials")

        files = (
            StoredFile.objects
            .filter(app=app, is_deleted=False)
            .order_by("-created_at")
        )

        data = [
            {
                "id": f.id,
                "url": _file_url(f.relative_path),
                "category": f.category,
                "mime_type": f.mime_type,
                "size_bytes": f.size_bytes,
                "original_name": f.original_name,
                "created_at": f.created_at,
            }
            for f in files
        ]

        return JsonResponse({"count": len(data), "results": data})

    except OriginNotAllowed as e:
        return JsonResponse({"error": str(e)}, status=403)

    except AuthenticationFailed as e:
        return JsonResponse({"error": str(e)}, status=403)

    except Exception as e:
        return JsonResponse(
            {"error": "Listing failed", "detail": str(e)},
            status=500,
        )

