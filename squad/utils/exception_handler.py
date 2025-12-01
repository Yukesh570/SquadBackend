# core/exception_handler.py
from rest_framework.views import exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Example: remove the "detail" key
        if isinstance(response.data, dict) and "detail" in response.data:
            message = response.data["detail"]
            response.data = {str(message)}  # rename key
            # OR, to remove the key completely and return just the message:
            # response.data = str(message)

    return response
