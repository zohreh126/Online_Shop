from django.conf import settings
from rest_framework import exceptions
from rest_framework.authentication import CSRFCheck
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header = self.get_header(request)

        # پشتیبانی از Authorization: Bearer <token>
        if header is not None:
            return super().authenticate(request)

        # دریافت JWT از Cookie امن
        raw_token = request.COOKIES.get(
            settings.AUTH_COOKIE_ACCESS
        )

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(
            raw_token.encode("utf-8")
        )

        # درخواست‌های Cookie-based باید CSRF داشته باشند
        self.enforce_csrf(request)

        return (
            self.get_user(validated_token),
            validated_token,
        )

    @staticmethod
    def enforce_csrf(request):
        def dummy_get_response(request):
            return None

        check = CSRFCheck(dummy_get_response)
        check.process_request(request)

        reason = check.process_view(
            request,
            None,
            (),
            {},
        )

        if reason:
            raise exceptions.PermissionDenied(
                f"CSRF Failed: {reason}"
            )
