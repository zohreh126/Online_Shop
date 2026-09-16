from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from products.models import Product

from .models import Address, Favorite, SiteFeedback
from .serializers import (
    AddressSerializer,
    CustomerProfileSerializer,
    CustomerRegistrationSerializer,
    FavoriteSerializer,
    FavoriteToggleSerializer,
    SiteFeedbackSerializer,
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


class SiteFeedbackListCreateView(generics.ListCreateAPIView):
    serializer_class = SiteFeedbackSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        queryset = SiteFeedback.objects.filter(is_active=True).select_related("customer")
        page = (self.request.query_params.get("page_path") or "").strip()
        if page:
            queryset = queryset.filter(page=page[:120])
        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        if not self.request.session.session_key:
            self.request.session.save()

        page = serializer.validated_data.get("page") or self.request.path
        if not page.startswith("/"):
            page = self.request.path

        customer = self.request.user if self.request.user.is_authenticated else None
        serializer.save(
            customer=customer,
            session_key=self.request.session.session_key or "",
            page=page[:120],
        )


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


class FavoriteViewSet(
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = FavoriteSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Favorite.objects.none()

        return (
            Favorite.objects.filter(
                customer=self.request.user,
                is_active=True,
                product__is_active=True,
            )
            .select_related("product", "product__category", "product__discount")
            .prefetch_related("product__category__children")
            .order_by("-created_at")
        )

    def perform_destroy(self, instance):
        instance.delete()

    @action(detail=False, methods=("post",), url_path="toggle")
    @transaction.atomic
    def toggle(self, request):
        input_serializer = FavoriteToggleSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        product = get_object_or_404(
            Product.objects.active(),
            pk=input_serializer.validated_data["product_id"],
        )
        favorite = Favorite.objects.filter(
            customer=request.user,
            product=product,
        ).first()

        if favorite and favorite.is_active:
            favorite.delete()
            return Response(
                {
                    "detail": "Favorite removed.",
                    "is_favorite": False,
                    "favorite": None,
                },
                status=status.HTTP_200_OK,
            )

        if favorite:
            favorite.is_active = True
            favorite.save(update_fields=("is_active", "updated_at"))
        else:
            favorite = Favorite.objects.create(
                customer=request.user,
                product=product,
            )

        return Response(
            {
                "detail": "Favorite added.",
                "is_favorite": True,
                "favorite": FavoriteSerializer(
                    favorite,
                    context={"request": request},
                ).data,
            },
            status=status.HTTP_200_OK,
        )
