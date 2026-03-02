import logging

logger = logging.getLogger("storage")


class StorageServiceError(Exception):
    """
    Base exception for all storage service errors.

    Attributes:
        message     → safe client message
        status_code → HTTP response code
        code        → machine-readable error code
    """

    status_code = 500
    code = "storage_error"

    def __init__(self, message=None, *, extra=None):
        self.message = message or "Storage service error"
        self.extra = extra or {}
        super().__init__(self.message)

    def log(self):
        logger.error(
            f"[{self.code}] {self.message}",
            extra=self.extra,
        )

class AuthenticationFailed(StorageServiceError):
    status_code = 403
    code = "auth_failed"


class OriginNotAllowed(StorageServiceError):
    status_code = 403
    code = "origin_not_allowed"


class FileMissing(StorageServiceError):
    status_code = 400
    code = "file_missing"


class ConflictError(StorageServiceError):
    status_code = 409
    code = "conflict"


class NotFoundError(StorageServiceError):
    status_code = 404
    code = "not_found"

class DatabaseError(StorageServiceError):
    status_code = 500
    code = "database_error"

class StorageWriteFailed(StorageServiceError):
    status_code = 507   # Insufficient Storage
    code = "storage_write_failed"


class StorageFull(StorageServiceError):
    status_code = 507
    code = "storage_full"


class FileDeleteFailed(StorageServiceError):
    status_code = 500
    code = "file_delete_failed"


class UpstreamServiceError(StorageServiceError):
    status_code = 502
    code = "upstream_error"


class TimeoutError(StorageServiceError):
    status_code = 504
    code = "timeout"