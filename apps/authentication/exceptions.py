"""
Custom Exception Handler - wraps DRF errors in our standard format.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_detail = response.data
        # Flatten simple string errors
        if isinstance(error_detail, list) and len(error_detail) == 1:
            message = str(error_detail[0])
            errors = None
        elif isinstance(error_detail, dict):
            # Extract non_field_errors or first key as message
            if "detail" in error_detail:
                message = str(error_detail.pop("detail"))
                errors = error_detail if error_detail else None
            else:
                message = "Validation error."
                errors = {k: [str(e) for e in v] if isinstance(v, list) else str(v)
                          for k, v in error_detail.items()}
        else:
            message = str(error_detail)
            errors = None

        response.data = {
            "success": False,
            "message": message,
            "data": None,
            "errors": errors,
        }

    return response
