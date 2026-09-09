from django.db import IntegrityError, transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Cart, CartItem, Order
from .serializers import (
    AdminOrderStatusSerializer,
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


def get_guest_cart(request):
    if not request.session.session_key:
        request.session.create()

    cart, _ = Cart.objects.get_or_create(
        session_key=request.session.session_key,
        defaults={"is_active": True},
    )
    if not cart.is_active:
        cart.is_active = True
        cart.save(update_fields=["is_active", "updated_at"])
    return cart


def get_request_cart(request):
    if request.user.is_authenticated:
        return get_active_cart(request.user)
    return get_guest_cart(request)


class CartDetailView(APIView):
    permission_classes = (permissions.AllowAny,)

    @extend_schema(responses=CartSerializer)
    def get(self, request):
        cart = get_request_cart(request)
        return Response(
            CartSerializer(cart, context={"request": request}).data
        )


class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = (permissions.AllowAny,)
    http_method_names = ("get", "post", "patch", "delete", "head", "options")

    def get_cart(self):
        return get_request_cart(self.request)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return CartItem.objects.none()

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

    @extend_schema(request=CheckoutSerializer, responses=OrderSerializer)
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
        if getattr(self, "swagger_fake_view", False):
            return Order.objects.none()

        return (
            Order.objects.filter(customer=self.request.user)
            .prefetch_related("items__product")
            .order_by("-created_at")
        )

    @action(detail=True, methods=["post"], url_path="pay")
    @transaction.atomic
    def pay(self, request, pk=None):
        order = self.get_queryset().select_for_update().get(pk=pk)

        if order.payment_method != Order.PaymentMethod.MOCK:
            return Response(
                {"detail": "Only mock payments are supported here."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if order.payment_status != Order.PaymentStatus.UNPAID:
            return Response(
                {"detail": "This order has already been processed for payment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if order.status == Order.Status.CANCELLED:
            return Response(
                {"detail": "Cancelled orders cannot be paid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.payment_status = Order.PaymentStatus.PAID
        order.status = Order.Status.CONFIRMED
        order.payment_reference = f"MOCK-{order.order_number}"
        order.paid_at = timezone.now()
        order.save(
            update_fields=[
                "payment_status",
                "status",
                "payment_reference",
                "paid_at",
                "updated_at",
            ]
        )

        return Response(OrderSerializer(order).data)


    @action(detail=True, methods=["post"], url_path="cancel")
    @transaction.atomic
    def cancel(self, request, pk=None):
        order = self.get_queryset().select_for_update().get(pk=pk)

        if order.status != Order.Status.PENDING:
            return Response(
                {"detail": "Only pending orders can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if order.payment_status != Order.PaymentStatus.UNPAID:
            return Response(
                {"detail": "Paid orders cannot be cancelled here."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = Order.Status.CANCELLED
        order.cancelled_at = timezone.now()
        order.save(update_fields=["status", "cancelled_at", "updated_at"])

        return Response(OrderSerializer(order).data)


class AdminOrderViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAdminUser,)
    http_method_names = ("get", "patch", "head", "options")

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Order.objects.none()

        return (
            Order.objects.all()
            .select_related("customer")
            .prefetch_related("items__product")
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "partial_update":
            return AdminOrderStatusSerializer
        return OrderSerializer
