class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class PermissionDenied(AppError):
    def __init__(self, message: str = "You do not have permission to do that.") -> None:
        super().__init__(message, 403)


class NotFound(AppError):
    def __init__(self, message: str = "Not found.") -> None:
        super().__init__(message, 404)


class Unauthorized(AppError):
    def __init__(self, message: str = "Sign in to continue.") -> None:
        super().__init__(message, 401)
