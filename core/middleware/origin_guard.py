from django.conf import settings
from django.http import JsonResponse


class OriginGuardMiddleware:
    """
    Production-level origin protection.

    Blocks requests coming from origins not listed in:
    settings.ALLOWED_SERVER_ORIGINS
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_origins = set(
            getattr(settings, "ALLOWED_SERVER_ORIGINS", [])
        )

    def __call__(self, request):

        origin = request.headers.get("Origin")
        referer = request.headers.get("Referer")

        request_origin = origin or referer

        # If no origin → allow (backend services / CLI)
        if request_origin:
            matched = any(
                request_origin.startswith(allowed)
                for allowed in self.allowed_origins
            )

            if not matched:
                return JsonResponse(
                    {
                        "error": "origin_not_allowed",
                        "detail": "Request origin is not permitted.",
                    },
                    status=403,
                )

        return self.get_response(request)