from copy import deepcopy
from datetime import timedelta

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q, Sum
from django.shortcuts import render
from django.utils import timezone

from customers.models import Customer, SiteFeedback
from orders.models import Order
from products.models import Discount, Product, ProductQuestion, ProductReview


_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


_ADMIN_COPY = {
    "fa": {
        "role_administrator": "مدیر کل",
        "role_product_manager": "مدیر محصولات",
        "role_supervisor": "ناظر",
        "role_operator": "اپراتور",
        "role_operational_user": "کاربر عملیاتی",
        "hero_kicker": "✦ NEXORA CONTROL CENTER",
        "hero_title": "مرکز فرماندهی فروشگاه",
        "hero_description": "ویترین، سفارش‌ها، مشتری‌ها و تجربه‌ی خرید را از یک فضای منظم مدیریت کن.",
        "daily_operations": "● عملیات روزانه",
        "live_data": "◌ داده‌های زنده‌ی فروشگاه",
        "view_store": "مشاهده فروشگاه",
        "quick_kicker": "NEXORA WORKBENCH",
        "quick_title": "عملیات سریع",
        "quick_description": "کارهای پرتکرار را بدون جست‌وجو در منوها شروع کن.",
        "quick_empty": "عملیات قابل دسترسی برای این نقش وجود ندارد.",
        "kpi_aria": "شاخص‌های زنده فروشگاه",
        "empty_kpi": "داده‌ای برای نمایش وجود ندارد.",
        "stat_aria": "دسترسی سریع",
        "products_showcase": "ویترین محصولات",
        "inventory_price": "مدیریت موجودی و قیمت",
        "categories": "دسته‌بندی‌ها",
        "tree_catalog": "ساختار درختی ویترین",
        "orders": "سفارش‌ها",
        "track_orders": "پیگیری و تغییر وضعیت",
        "customers": "مشتری‌ها",
        "accounts_roles": "حساب‌ها و نقش‌ها",
        "discounts": "تخفیف‌ها",
        "product_campaigns": "کمپین‌های محصولی",
        "customer_reviews": "نظرات کاربران",
        "review_quality": "بررسی کیفیت تجربه",
        "product_questions": "پرسش‌های محصول",
        "answer_customers": "پاسخ به سؤال‌های مشتریان",
        "panels_aria": "نمایش سریع فعالیت‌ها",
        "live_orders": "آخرین سفارش‌ها",
        "view_all": "مشاهده همه",
        "order_empty": "هنوز سفارشی برای نمایش ثبت نشده است.",
        "customer_voice": "آخرین نظرها",
        "manage_reviews": "مدیریت نظرها",
        "review_empty": "هنوز نظر محصولی برای نمایش ثبت نشده است.",
        "no_title": "بدون عنوان",
        "product_qa": "آخرین پرسش‌ها",
        "manage_questions": "مدیریت پرسش‌ها",
        "answered": "پاسخ داده شد",
        "unanswered": "بی‌پاسخ",
        "question_empty": "هنوز پرسشی برای نمایش ثبت نشده است.",
        "ops_aria": "هشدارهای عملیاتی فروشگاه",
        "inventory_watch": "موجودی رو به اتمام",
        "manage_inventory": "مدیریت موجودی",
        "stock_unit": "عدد",
        "inventory_empty": "همه‌ی محصولات فعال موجودی مناسبی دارند.",
        "promotion_radar": "تخفیف‌های رو به پایان",
        "manage_campaigns": "مدیریت کمپین‌ها",
        "promotion_empty": "در هفت روز آینده کمپینی منقضی نمی‌شود.",
        "site_pulse": "نبض تجربه‌ی مشتری",
        "customer_experience": "تجربه‌ی مشتری",
        "view_feedback": "مشاهده بازخوردها",
        "guest": "مهمان فروشگاه",
        "no_comment": "بدون توضیح",
        "feedback_empty": "هنوز بازخوردی برای نمایش ثبت نشده است.",
        "recent_activity": "آخرین فعالیت‌ها",
        "my_activity": "فعالیت‌های من",
        "no_activity": "هنوز فعالیتی ثبت نشده است.",
        "added": "افزوده شد:",
        "changed": "تغییر کرد:",
        "deleted": "حذف شد:",
        "unknown_item": "مورد نامشخص",
        "currency": "تومان",
        "action_add_product": "افزودن محصول",
        "hint_add_product": "ساخت محصول جدید در ویترین",
        "action_add_category": "افزودن دسته‌بندی",
        "hint_add_category": "ساختار درختی ویترین",
        "action_add_discount": "ساخت تخفیف",
        "hint_add_discount": "قیمت‌گذاری ویژه برای محصول",
        "action_review_orders": "بررسی سفارش‌ها",
        "hint_review_orders": "پیگیری وضعیت خریدها",
        "action_review_reviews": "بررسی نظرات",
        "hint_review_reviews": "مدیریت صدای مشتریان",
        "action_review_questions": "پرسش‌های محصول",
        "hint_review_questions": "پاسخ به سؤال‌های مشتریان",
        "metric_active_products": "محصولات فعال",
        "hint_active_products": "در ویترین فروشگاه",
        "metric_discounted_products": "محصولات تخفیف‌دار",
        "hint_discounted_products": "کمپین‌های فعال امروز",
        "metric_orders": "سفارش‌ها",
        "hint_orders": "در حال پیگیری",
        "metric_paid_sales": "فروش پرداخت‌شده",
        "hint_paid_sales": "جمع سفارش‌های موفق",
        "metric_active_customers": "مشتری‌های فعال",
        "hint_active_customers": "حساب‌های مشتری فروشگاه",
        "metric_published_reviews": "نظرهای منتشرشده",
        "hint_published_reviews": "بازخورد قابل نمایش در فروشگاه",
        "metric_unanswered_questions": "پرسش‌های بی‌پاسخ",
        "hint_unanswered_questions": "در انتظار پاسخ تیم",
        "status_pending": "در انتظار",
        "status_confirmed": "تأییدشده",
        "status_processing": "در حال پردازش",
        "status_shipped": "ارسال‌شده",
        "status_delivered": "تحویل‌شده",
        "status_cancelled": "لغوشده",
        "status_refunded": "مستردشده",
        "discount_percentage": "درصدی",
        "discount_fixed": "مبلغ ثابت",
        "app_auth": "احراز هویت و مجوزها",
        "app_customers": "مشتریان",
        "app_products": "محصولات",
        "app_orders": "سفارش‌ها",
    },
    "en": {
        "role_administrator": "Administrator",
        "role_product_manager": "Product manager",
        "role_supervisor": "Supervisor",
        "role_operator": "Operator",
        "role_operational_user": "Operations user",
        "hero_kicker": "✦ NEXORA CONTROL CENTER",
        "hero_title": "Store control center",
        "hero_description": "Manage the catalog, orders, customers, and shopping experience from one focused workspace.",
        "daily_operations": "● Daily operations",
        "live_data": "◌ Live store data",
        "view_store": "View storefront",
        "quick_kicker": "NEXORA WORKBENCH",
        "quick_title": "Quick operations",
        "quick_description": "Start frequent tasks without searching through menus.",
        "quick_empty": "No operations are available for this role.",
        "kpi_aria": "Live store metrics",
        "empty_kpi": "There is no data to display.",
        "stat_aria": "Quick access",
        "products_showcase": "Product showcase",
        "inventory_price": "Manage inventory and pricing",
        "categories": "Categories",
        "tree_catalog": "Tree-based storefront structure",
        "orders": "Orders",
        "track_orders": "Track and update status",
        "customers": "Customers",
        "accounts_roles": "Accounts and roles",
        "discounts": "Discounts",
        "product_campaigns": "Product campaigns",
        "customer_reviews": "Customer reviews",
        "review_quality": "Review experience quality",
        "product_questions": "Product questions",
        "answer_customers": "Answer customer questions",
        "panels_aria": "Recent activity overview",
        "live_orders": "Latest orders",
        "view_all": "View all",
        "order_empty": "No orders have been recorded yet.",
        "customer_voice": "Latest reviews",
        "manage_reviews": "Manage reviews",
        "review_empty": "No product reviews are available yet.",
        "no_title": "Untitled",
        "product_qa": "Latest questions",
        "manage_questions": "Manage questions",
        "answered": "Answered",
        "unanswered": "Waiting for answer",
        "question_empty": "No product questions are available yet.",
        "ops_aria": "Store operations alerts",
        "inventory_watch": "Low stock",
        "manage_inventory": "Manage inventory",
        "stock_unit": "items",
        "inventory_empty": "All active products have healthy stock levels.",
        "promotion_radar": "Discounts ending soon",
        "manage_campaigns": "Manage campaigns",
        "promotion_empty": "No campaign expires in the next seven days.",
        "site_pulse": "Customer experience pulse",
        "customer_experience": "Customer experience",
        "view_feedback": "View feedback",
        "guest": "Store guest",
        "no_comment": "No comment",
        "feedback_empty": "No feedback has been submitted yet.",
        "recent_activity": "Recent activity",
        "my_activity": "My activity",
        "no_activity": "No activity has been recorded yet.",
        "added": "Added:",
        "changed": "Changed:",
        "deleted": "Deleted:",
        "unknown_item": "Unknown item",
        "currency": "Toman",
        "action_add_product": "Add product",
        "hint_add_product": "Create a new storefront product",
        "action_add_category": "Add category",
        "hint_add_category": "Build the storefront tree",
        "action_add_discount": "Create discount",
        "hint_add_discount": "Set a special product price",
        "action_review_orders": "Review orders",
        "hint_review_orders": "Track purchase status",
        "action_review_reviews": "Review feedback",
        "hint_review_reviews": "Manage the customer voice",
        "action_review_questions": "Product questions",
        "hint_review_questions": "Answer customer questions",
        "metric_active_products": "Active products",
        "hint_active_products": "Published in the storefront",
        "metric_discounted_products": "Discounted products",
        "hint_discounted_products": "Active campaigns today",
        "metric_orders": "Orders",
        "hint_orders": "being followed up",
        "metric_paid_sales": "Paid sales",
        "hint_paid_sales": "Successful order total",
        "metric_active_customers": "Active customers",
        "hint_active_customers": "Store customer accounts",
        "metric_published_reviews": "Published reviews",
        "hint_published_reviews": "Feedback visible in the storefront",
        "metric_unanswered_questions": "Unanswered questions",
        "hint_unanswered_questions": "Waiting for the team",
        "status_pending": "Pending",
        "status_confirmed": "Confirmed",
        "status_processing": "Processing",
        "status_shipped": "Shipped",
        "status_delivered": "Delivered",
        "status_cancelled": "Cancelled",
        "status_refunded": "Refunded",
        "discount_percentage": "Percentage",
        "discount_fixed": "Fixed amount",
        "app_auth": "Authentication and Authorization",
        "app_customers": "Customers",
        "app_products": "Products",
        "app_orders": "Orders",
    },
}


_MODEL_LABELS_FA = {
    "customers": {
        "Customer": "مشتری‌ها",
        "Address": "نشانی‌ها",
        "Favorite": "علاقه‌مندی‌ها",
        "ProductWatch": "دنبال‌کردن محصولات",
        "SiteFeedback": "بازخوردهای سایت",
        "CustomerNotification": "اعلان‌های مشتری",
    },
    "products": {
        "Category": "دسته‌بندی‌ها",
        "Product": "محصولات",
        "ProductReview": "نظرات محصولات",
        "ProductReviewHelpfulVote": "رأی‌های مفیدبودن نظر",
        "ProductQuestion": "پرسش‌های محصولات",
        "Discount": "تخفیف‌ها",
        "DiscountCode": "کدهای تخفیف",
    },
    "orders": {
        "Cart": "سبدهای خرید",
        "CartItem": "آیتم‌های سبد خرید",
        "Order": "سفارش‌ها",
        "OrderItem": "آیتم‌های سفارش",
        "RewardTransaction": "تراکنش‌های امتیاز",
    },
}


_ORDER_STATUS_KEYS = {
    "pending": "status_pending",
    "confirmed": "status_confirmed",
    "processing": "status_processing",
    "shipped": "status_shipped",
    "delivered": "status_delivered",
    "cancelled": "status_cancelled",
    "refunded": "status_refunded",
}


def _language(request):
    return "en" if (getattr(request, "LANGUAGE_CODE", "fa") or "fa").startswith("en") else "fa"


def _format_number(value, language):
    text = f"{int(value):,}" if isinstance(value, (int, float)) else str(value)
    return text.translate(_PERSIAN_DIGITS) if language == "fa" else text


def _format_money(value, language, copy):
    amount = int(value or 0)
    formatted = f"{amount:,}"
    if language == "fa":
        formatted = formatted.replace(",", "٬").translate(_PERSIAN_DIGITS)
    return f"{formatted} {copy['currency']}"


def _format_datetime(value, language):
    text = timezone.localtime(value).strftime("%Y/%m/%d %H:%M")
    return text.translate(_PERSIAN_DIGITS) if language == "fa" else text


def _can_access(user, app_label, model_name):
    return user.is_superuser or any(
        user.has_perm(f"{app_label}.{action}_{model_name}")
        for action in ("view", "change", "add", "delete")
    )


def _can_add(user, app_label, model_name):
    return user.is_superuser or user.has_perm(f"{app_label}.add_{model_name}")


def _localized_app_list(request, language, copy):
    app_list = deepcopy(admin.site.get_app_list(request))
    app_labels = {
        "auth": copy["app_auth"],
        "customers": copy["app_customers"],
        "products": copy["app_products"],
        "orders": copy["app_orders"],
    }
    for app in app_list:
        app["name"] = app_labels.get(app.get("app_label"), app["name"])
        if language != "fa":
            continue
        for model in app.get("models", []):
            model["name"] = _MODEL_LABELS_FA.get(app.get("app_label"), {}).get(
                model.get("object_name"), model["name"]
            )
    return app_list


def _decorate_order(order, language, copy):
    order.nexora_total_display = _format_money(order.total_amount, language, copy)
    order.nexora_created_display = _format_datetime(order.created_at, language)
    status_key = _ORDER_STATUS_KEYS.get(order.status)
    order.nexora_status_display = copy.get(status_key, order.get_status_display())
    return order


def _decorate_discount(discount, language, copy):
    if discount.discount_type == Discount.DiscountType.PERCENTAGE:
        value = _format_number(discount.value, language)
        discount.nexora_value_display = f"{value}%"
        discount.nexora_type_display = copy["discount_percentage"]
    else:
        discount.nexora_value_display = _format_money(discount.value, language, copy)
        discount.nexora_type_display = copy["discount_fixed"]
    discount.nexora_ends_display = _format_datetime(discount.ends_at, language)
    return discount


@staff_member_required
def nexora_admin_index(request):
    """Render a data-rich, genuinely bilingual home for the Django admin."""
    language = _language(request)
    copy = _ADMIN_COPY[language]
    context = admin.site.each_context(request)
    context.update(
        {
            "title": copy["hero_title"],
            "subtitle": None,
            "app_list": _localized_app_list(request, language, copy),
            "nexora_copy": copy,
            "nexora_metrics": [],
            "nexora_quick_actions": [],
            "nexora_recent_orders": [],
            "nexora_recent_reviews": [],
            "nexora_recent_questions": [],
            "nexora_low_stock_products": [],
            "nexora_expiring_discounts": [],
            "nexora_recent_feedback": [],
            "nexora_admin_role": "",
            "nexora_admin_identity": "",
        }
    )

    user = request.user
    role_labels = {
        Customer.Role.PRODUCT_MANAGER: copy["role_product_manager"],
        Customer.Role.SUPERVISOR: copy["role_supervisor"],
        Customer.Role.OPERATOR: copy["role_operator"],
    }
    context["nexora_admin_role"] = (
        copy["role_administrator"]
        if user.is_superuser
        else role_labels.get(getattr(user, "role", ""), copy["role_operational_user"])
    )
    context["nexora_admin_identity"] = f"{user.first_name} {user.last_name}".strip() or user.username
    metrics = []
    quick_actions = []

    if _can_add(user, "products", "product"):
        quick_actions.append(
            {
                "icon": "+",
                "label": copy["action_add_product"],
                "hint": copy["hint_add_product"],
                "url": "admin:products_product_add",
                "tone": "purple",
            }
        )

    if _can_add(user, "products", "category"):
        quick_actions.append(
            {
                "icon": "⌘",
                "label": copy["action_add_category"],
                "hint": copy["hint_add_category"],
                "url": "admin:products_category_add",
                "tone": "coral",
            }
        )

    if _can_add(user, "products", "discount"):
        quick_actions.append(
            {
                "icon": "%",
                "label": copy["action_add_discount"],
                "hint": copy["hint_add_discount"],
                "url": "admin:products_discount_add",
                "tone": "gold",
            }
        )

    if _can_access(user, "orders", "order"):
        quick_actions.append(
            {
                "icon": "▣",
                "label": copy["action_review_orders"],
                "hint": copy["hint_review_orders"],
                "url": "admin:orders_order_changelist",
                "tone": "green",
            }
        )

    if _can_access(user, "products", "productreview"):
        quick_actions.append(
            {
                "icon": "★",
                "label": copy["action_review_reviews"],
                "hint": copy["hint_review_reviews"],
                "url": "admin:products_productreview_changelist",
                "tone": "blue",
            }
        )

    if _can_access(user, "products", "productquestion"):
        quick_actions.append(
            {
                "icon": "?",
                "label": copy["action_review_questions"],
                "hint": copy["hint_review_questions"],
                "url": "admin:products_productquestion_changelist",
                "tone": "blue",
            }
        )

    if _can_access(user, "products", "product"):
        metrics.append(
            {
                "icon": "◈",
                "label": copy["metric_active_products"],
                "value": _format_number(Product.objects.filter(is_active=True).count(), language),
                "hint": copy["hint_active_products"],
                "url": "admin:products_product_changelist",
                "tone": "purple",
            }
        )
        low_stock_products = list(
            Product.objects.filter(is_active=True, stock_quantity__lte=5)
            .order_by("stock_quantity", "name")[:6]
        )
        for product in low_stock_products:
            product.nexora_stock_display = f"{_format_number(product.stock_quantity, language)} {copy['stock_unit']}"
        context["nexora_low_stock_products"] = low_stock_products

    if _can_access(user, "products", "discount"):
        now = timezone.now()
        active_discount_filter = (
            Q(is_active=True)
            & (Q(starts_at__isnull=True) | Q(starts_at__lte=now))
            & (Q(ends_at__isnull=True) | Q(ends_at__gte=now))
        )
        discounted_products = Product.objects.filter(
            is_active=True,
            discount__in=Discount.objects.filter(active_discount_filter),
        ).count()
        metrics.append(
            {
                "icon": "%",
                "label": copy["metric_discounted_products"],
                "value": _format_number(discounted_products, language),
                "hint": copy["hint_discounted_products"],
                "url": "admin:products_discount_changelist",
                "tone": "coral",
            }
        )
        expiring_discounts = list(
            Discount.objects.filter(
                active_discount_filter,
                product__is_active=True,
                ends_at__isnull=False,
                ends_at__lte=now + timedelta(days=7),
            )
            .select_related("product")
            .order_by("ends_at")[:6]
        )
        context["nexora_expiring_discounts"] = [
            _decorate_discount(discount, language, copy) for discount in expiring_discounts
        ]

    if _can_access(user, "orders", "order"):
        order_queryset = Order.objects.all()
        pending_count = order_queryset.filter(
            status__in=(Order.Status.PENDING, Order.Status.CONFIRMED, Order.Status.PROCESSING)
        ).count()
        revenue = order_queryset.filter(payment_status=Order.PaymentStatus.PAID).aggregate(
            total=Sum("total_amount")
        )["total"]
        metrics.append(
            {
                "icon": "▣",
                "label": copy["metric_orders"],
                "value": _format_number(order_queryset.count(), language),
                "hint": f"{_format_number(pending_count, language)} {copy['hint_orders']}",
                "url": "admin:orders_order_changelist",
                "tone": "green",
            }
        )
        metrics.append(
            {
                "icon": "↗",
                "label": copy["metric_paid_sales"],
                "value": _format_money(revenue, language, copy),
                "hint": copy["hint_paid_sales"],
                "url": "admin:orders_order_changelist",
                "tone": "gold",
            }
        )
        context["nexora_recent_orders"] = [
            _decorate_order(order, language, copy)
            for order in order_queryset.select_related("customer").order_by("-created_at")[:5]
        ]

    if _can_access(user, "customers", "customer"):
        metrics.append(
            {
                "icon": "♙",
                "label": copy["metric_active_customers"],
                "value": _format_number(
                    Customer.objects.filter(is_active=True, is_staff=False).count(), language
                ),
                "hint": copy["hint_active_customers"],
                "url": "admin:customers_customer_changelist",
                "tone": "blue",
            }
        )

    if _can_access(user, "products", "productreview"):
        metrics.append(
            {
                "icon": "★",
                "label": copy["metric_published_reviews"],
                "value": _format_number(
                    ProductReview.objects.filter(is_active=True, is_approved=True).count(), language
                ),
                "hint": copy["hint_published_reviews"],
                "url": "admin:products_productreview_changelist",
                "tone": "mint",
            }
        )
        recent_reviews = list(
            ProductReview.objects.filter(is_active=True)
            .select_related("product", "customer")
            .order_by("-created_at")[:5]
        )
        for review in recent_reviews:
            review.nexora_title_display = review.title or copy["no_title"]
            review.nexora_rating_display = _format_number(review.rating, language)
        context["nexora_recent_reviews"] = recent_reviews

    if _can_access(user, "products", "productquestion"):
        question_queryset = ProductQuestion.objects.filter(is_active=True, is_approved=True)
        unanswered_count = question_queryset.filter(answer="").count()
        metrics.append(
            {
                "icon": "?",
                "label": copy["metric_unanswered_questions"],
                "value": _format_number(unanswered_count, language),
                "hint": copy["hint_unanswered_questions"],
                "url": "admin:products_productquestion_changelist",
                "tone": "blue",
            }
        )
        context["nexora_recent_questions"] = list(
            question_queryset.select_related("product", "customer").order_by("-created_at")[:5]
        )

    if _can_access(user, "customers", "sitefeedback"):
        recent_feedback = list(
            SiteFeedback.objects.filter(is_active=True)
            .select_related("customer")
            .order_by("-created_at")[:5]
        )
        for feedback in recent_feedback:
            feedback.nexora_comment_display = feedback.comment or copy["no_comment"]
            feedback.nexora_rating_display = _format_number(feedback.rating, language)
        context["nexora_recent_feedback"] = recent_feedback

    context["nexora_metrics"] = metrics
    context["nexora_quick_actions"] = quick_actions
    return render(request, "admin/index.html", context)
