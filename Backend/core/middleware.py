from django.utils.deprecation import MiddlewareMixin


class NoCacheDuringDevMiddleware(MiddlewareMixin):
    """
    Prevent browsers from caching dynamic HTML responses during development.
    Forces browsers like Google Chrome to always fetch fresh pages on refresh.
    """

    def process_response(self, request, response):
        content_type = response.get("Content-Type", "")
        if "text/html" in content_type:
            response["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"
        return response

