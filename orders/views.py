from django.db import IntegrityError, transaction
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Cart, CartItem, Order
from .serializers import (
    CartItemSerializer,
    CartSerializer,
    CheckoutSerializer,
    OrderSerializer,
)


def get_active_cart(customer):
    """Return the customer's active cart, creating it when necessary."""
    try:
        with transaction.atomic():
            cart, _ = Cart.objects.get_or_create(
                customer=customer,
                is_active=True,
            )
            return cart
    except IntegrityError:
        return Cart.objects.get(
            customer=customer,
            is_active=True,
        )


class CartDetailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        cart = get_active_cart(request.user)
        return Response(CartSerializer(cart).data)


class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ("get", "post", "patch", "delete", "head", "options")

    def get_cart(self):
        return get_active_cart(self.request.user)

    def get_queryset(self):
        return (
            CartItem.objects.filter(cart=self.get_cart())
            .select_related("product")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["cart"] = self.get_cart()
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = serializer.save()
        return Response(
            self.get_serializer(item).data,
            status=status.HTTP_201_CREATED,
        )


class CheckoutView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = CheckoutSerializer(
            data=request.data,
            context={
                "request": request,
                "cart": get_active_cart(request.user),
            },
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return (
            Order.objects.filter(customer=self.request.user)
            .prefetch_related("items__product")
            .order_by("-created_at")
        )
