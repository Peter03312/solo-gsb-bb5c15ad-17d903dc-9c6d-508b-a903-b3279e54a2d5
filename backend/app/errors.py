"""Domain errors. Routers raise these; handlers in main.py turn them into HTTP responses."""


class DomainError(Exception):
    status_code = 400

    def __init__(self, message: str, **extra):
        super().__init__(message)
        self.message = message
        self.extra = extra

    def to_dict(self) -> dict:
        return {"detail": self.message, **self.extra}


class ValidationError(DomainError):
    status_code = 422


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    status_code = 409


class UploadError(DomainError):
    status_code = 400
