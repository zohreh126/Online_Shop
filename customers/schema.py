from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CookieJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "customers.authentication.CookieJWTAuthentication"
    name = "cookieJWT"
    match_subclasses = True

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": "access_token",
            "description": "HTTP-only access token cookie.",
        }
