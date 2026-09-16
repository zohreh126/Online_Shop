from django.db import IntegrityError, transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import Product

from .models import Cart, CartItem, Order, RewardTransaction
from .rewards import calculate_order_reward_points
from .serializers import (
    AdminOrderStatusSerializer,
    CartItemSerializer,
    CartSerializer,
    CheckoutSerializer,
    CouponSerializer,
    MockPaymentSerializer,
    OrderSerializer,
    ReorderResultSerializer,
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


class CartCouponView(APIView):
    permission_classes = (permissions.AllowAny,)

    @extend_schema(request=CouponSerializer, responses=CartSerializer)
    def post(self, request):
        cart = get_request_cart(request)
        if not cart.items.exists():
            return Response(
                {"detail": "Cannot apply a coupon to an empty cart."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CouponSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]

        from products.models import DiscountCode

        try:
            discount_code = DiscountCode.objects.get(code=code)
        except DiscountCode.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"code": "Invalid discount code."}
            ) from exc

        if not discount_code.is_valid_now:
            return Response(
                {"code": "This discount code is no longer valid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if cart.subtotal < discount_code.minimum_order_amount:
            return Response(
                {"code": "The cart does not meet the minimum amount."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart.discount_code = discount_code
        cart.save(update_fields=["discount_code", "updated_at"])
        return Response(
            CartSerializer(cart, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(request=None, responses={204: None})
    def delete(self, request):
        cart = get_request_cart(request)
        cart.discount_code = None
        cart.save(update_fields=["discount_code", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


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
    lookup_field = "order_number"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Order.objects.none()

        return (
            Order.objects.filter(customer=self.request.user)
            .prefetch_related("items__product")
            .order_by("-created_at")
        )

    @transaction.atomic
    def _process_mock_payment(self, order, result):
        order = Order.objects.select_for_update().get(pk=order.pk)

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

        if result == "failed":
            order.payment_status = Order.PaymentStatus.FAILED
            order.status = Order.Status.CANCELLED
            order.cancelled_at = timezone.now()
            order.save(
                update_fields=["payment_status", "status", "cancelled_at", "updated_at"]
            )
            return Response(OrderSerializer(order).data)

        if order.discount_code_id:
            discount_code = order.discount_code
            if not discount_code.is_valid_now:
                return Response(
                    {"detail": "The order coupon is no longer valid."},
                    status=status.HTTP_409_CONFLICT,
                )

        order_items = list(
            order.items.select_for_update().select_related("product")
        )
        for order_item in order_items:
            if order_item.product_id is None:
                continue

            product = order_item.product
            if not product.is_active or product.stock_quantity < order_item.quantity:
                return Response(
                    {"detail": "Stock is no longer available for this order."},
                    status=status.HTTP_409_CONFLICT,
                )

        for order_item in order_items:
            if order_item.product_id is None:
                continue
            product = order_item.product
            product.stock_quantity -= order_item.quantity
            product.save(update_fields=["stock_quantity", "updated_at"])

        if order.discount_code_id:
            discount_code.used_count += 1
            discount_code.save(update_fields=["used_count", "updated_at"])

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
        reward_points = calculate_order_reward_points(order.total_amount)
        if reward_points:
            RewardTransaction.objects.get_or_create(
                order=order,
                defaults={
                    "customer": order.customer,
                    "points": reward_points,
                    "reason": "Nexora order reward",
                },
            )

        CartItem.objects.filter(
            cart__customer=order.customer,
            cart__is_active=True,
            product_id__in=[item.product_id for item in order_items if item.product_id],
        ).delete()
        Cart.objects.filter(
            customer=order.customer,
            is_active=True,
        ).update(discount_code=None)
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["post"], url_path="pay")
    @transaction.atomic
    def pay(self, request, *args, **kwargs):
        order = self.get_queryset().select_for_update().get(
            order_number=kwargs["order_number"],
        )
        return self._process_mock_payment(order, "success")

    @extend_schema(request=MockPaymentSerializer, responses=OrderSerializer)
    @action(detail=True, methods=["post"], url_path="mock-payment")
    def mock_payment(self, request, *args, **kwargs):
        order = self.get_queryset().select_for_update().get(
            order_number=kwargs["order_number"],
        )
        serializer = MockPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._process_mock_payment(
            order,
            serializer.validated_data["result"],
        )

    @extend_schema(request=None, responses=ReorderResultSerializer)
    @action(detail=True, methods=["post"], url_path="reorder")
    @transaction.atomic
    def reorder(self, request, *args, **kwargs):
        order = self.get_object()
        cart = get_active_cart(request.user)
        cart = Cart.objects.select_for_update().get(pk=cart.pk)
        existing_items = {
            item.product_id: item
            for item in CartItem.objects.select_for_update().filter(cart=cart)
        }
        added = []
        skipped = []

        order_items = order.items.select_related("product").order_by("id")
        if not order_items.exists():
            return Response(
                {"detail": "This order has no items that can be reordered."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for order_item in order_items:
            product_name = order_item.product_name
            if order_item.product_id is None:
                skipped.append(
                    {
                        "product_name": product_name,
                        "reason": "The original product is no longer available.",
                    }
                )
                continue

            product = Product.objects.select_for_update().filter(
                pk=order_item.product_id,
                is_active=True,
            ).first()
            if product is None:
                skipped.append(
                    {
                        "product_name": product_name,
                        "reason": "The product is no longer available.",
                    }
                )
                continue

            existing_item = existing_items.get(product.pk)
            current_quantity = existing_item.quantity if existing_item else 0
            available_quantity = product.stock_quantity - current_quantity
            if available_quantity <= 0:
                skipped.append(
                    {
                        "product_name": product_name,
                        "reason": "There is no more stock available for this product.",
                    }
                )
                continue

            quantity = min(order_item.quantity, available_quantity)
            if existing_item is None:
                existing_item = CartItem.objects.create(
                    cart=cart,
                    product=product,
                    quantity=quantity,
                )
                existing_items[product.pk] = existing_item
            else:
                existing_item.quantity += quantity
                existing_item.save(update_fields=["quantity", "updated_at"])

            added.append(
                {
                    "product_id": product.pk,
                    "product_name": product.name,
                    "quantity": quantity,
                }
            )
            if quantity < order_item.quantity:
                skipped.append(
                    {
                        "product_name": product_name,
                        "reason": "Only the currently available quantity was added.",
                    }
                )

        if not added:
            return Response(
                {
                    "detail": "No items from this order are currently available.",
                    "added": added,
                    "skipped": skipped,
                    "cart": CartSerializer(cart, context={"request": request}).data,
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "added": added,
                "skipped": skipped,
                "cart": CartSerializer(cart, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="cancel")
    @transaction.atomic
    def cancel(self, request, *args, **kwargs):
        order = self.get_queryset().select_for_update().get(
            order_number=kwargs["order_number"],
        )

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
