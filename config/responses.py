from django.http import JsonResponse
from .exceptions import StorageServiceError


def error_response(exc: Exception):
    """
    Convert exceptions into safe JSON responses.
    """

    if isinstance(exc, StorageServiceError):
        exc.log()
        return JsonResponse(
            {
                "error": exc.code,
                "message": exc.message,
            },
            status=exc.status_code,
        )

    return JsonResponse(
        {
            "error": "internal_error",
            "message": "Internal server error",
        },
        status=500,
    )