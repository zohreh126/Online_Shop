from rest_framework import generics, permissions

from .serializers import (
    CustomerProfileSerializer,
    CustomerRegistrationSerializer,
)


class CustomerRegistrationView(generics.CreateAPIView):
    serializer_class = CustomerRegistrationSerializer
    permission_classes = (permissions.AllowAny,)


class CustomerProfileView(generics.RetrieveAPIView):
    serializer_class = CustomerProfileSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user
