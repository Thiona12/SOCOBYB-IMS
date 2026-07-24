"""Normalizes DRF errors into D-12 §15's error shape: { error: { code, message } }."""
from rest_framework.views import exception_handler
from rest_framework.response import Response


def socobys_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    code = getattr(exc, "default_code", "ERROR").upper() if hasattr(exc, "default_code") else "ERROR"
    if response.status_code == 401:
        code = "UNAUTHORIZED"
    elif response.status_code == 403:
        code = "FORBIDDEN"
    elif response.status_code == 404:
        code = "NOT_FOUND"
    elif response.status_code == 400 or response.status_code == 422:
        code = "VALIDATION_ERROR"

    message = response.data
    if isinstance(message, dict) and "detail" in message:
        message = message["detail"]

    response.data = {"error": {"code": code, "message": str(message)}}
    return response
