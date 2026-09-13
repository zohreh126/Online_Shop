from rest_framework import generics, permissions, viewsets

from .models import Address
from .serializers import (
    AddressSerializer,
    CustomerProfileSerializer,
    CustomerRegistrationSerializer,
)


class CustomerRegistrationView(generics.CreateAPIView):
    serializer_class = CustomerRegistrationSerializer
    permission_classes = (permissions.AllowAny,)


class CustomerProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            from .serializers import CustomerProfileUpdateSerializer
            return CustomerProfileUpdateSerializer
        return CustomerProfileSerializer


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Address.objects.none()

        return Address.objects.filter(
            customer=self.request.user,
            is_active=True,
        ).order_by("-is_default", "-id")

    def perform_destroy(self, instance):
        instance.delete()
