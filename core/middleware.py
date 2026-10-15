"""
Security headers middleware for DailyJob.
Adds essential security headers to all HTTP responses:
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy: camera=(self), microphone=(), geolocation=()
"""

class SecurityHeadersMiddleware:
    """
    Middleware to inject security headers on all HTTP responses.
    Ensures security headers are returned for both API requests and static HTML pages.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if hasattr(response, 'headers'):
            response.headers.setdefault('X-Content-Type-Options', 'nosniff')
            response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
            response.headers.setdefault('Permissions-Policy', 'camera=(self), microphone=(), geolocation=()')
        else:
            if not response.has_header('X-Content-Type-Options'):
                response['X-Content-Type-Options'] = 'nosniff'
            if not response.has_header('Referrer-Policy'):
                response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            if not response.has_header('Permissions-Policy'):
                response['Permissions-Policy'] = 'camera=(self), microphone=(), geolocation=()'
        return response
