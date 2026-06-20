"""
Utility: Consistent API response format across all endpoints.
"""
from rest_framework.response import Response


def api_response(data=None, message="", errors=None, status_code=200):
    """
    Standardized API response format:
    {
        "success": true/false,
        "message": "...",
        "data": {...} | null,
        "errors": {...} | null
    }
    """
    return Response(
        {
            "success": errors is None,
            "message": message,
            "data": data,
            "errors": errors,
        },
        status=status_code,
    )
