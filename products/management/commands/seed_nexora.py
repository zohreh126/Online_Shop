from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from products.models import Category, Product


CATALOG = {
    "کیبورد و ماوس": {
        "slug": "keyboards-mice",
        "products": [
            {
                "name": "Nexora Flux Mechanical Keyboard",
                "sku": "NX-FLUX-KB-001",
                "brand": "Nexora",
                "price": Decimal("4890000.00"),
                "stock_quantity": 18,
                "description": "کیبورد مکانیکال مینیمال با نورپردازی قابل تنظیم برای کار و بازی.",
                "specifications": {
                    "switch": "Hot-swap linear",
                    "layout": "75% / US",
                    "connection": "USB-C, Bluetooth",
                    "backlight": "RGB",
                },
            },
            {
                "name": "Nexora Arc Wireless Mouse",
                "sku": "NX-ARC-MOUSE-001",
                "brand": "Nexora",
                "price": Decimal("2190000.00"),
                "stock_quantity": 32,
                "description": "ماوس بی‌سیم سبک با سنسور دقیق و طراحی ارگونومیک.",
                "specifications": {
                    "sensor": "PAW3395",
                    "dpi": 26000,
                    "connection": "2.4GHz, Bluetooth",
                    "weight_g": 60,
                },
            },
        ],
    },
    "صوتی": {
        "slug": "audio",
        "products": [
            {
                "name": "Nexora Pulse ANC Headphones",
                "sku": "NX-PULSE-ANC-001",
                "brand": "Nexora",
                "price": Decimal("6790000.00"),
                "stock_quantity": 14,
                "description": "هدفون بی‌سیم دورگوشی با حذف نویز فعال و صدای متعادل.",
                "specifications": {
                    "anc": True,
                    "battery_hours": 40,
                    "connection": "Bluetooth 5.3",
                    "charging": "USB-C",
                },
            },
            {
                "name": "Nexora Echo USB Microphone",
                "sku": "NX-ECHO-MIC-001",
                "brand": "Nexora",
                "price": Decimal("3590000.00"),
                "stock_quantity": 9,
                "description": "میکروفون USB رومیزی برای استریم، جلسه و تولید محتوا.",
                "specifications": {
                    "pickup": "Cardioid",
                    "sample_rate": "96kHz",
                    "connection": "USB-C",
                    "monitoring": "3.5mm headphone jack",
                },
            },
        ],
    },
    "کابل و شارژ": {
        "slug": "cables-charging",
        "products": [
            {
                "name": "Nexora Link USB-C Cable 100W",
                "sku": "NX-LINK-C100-001",
                "brand": "Nexora",
                "price": Decimal("790000.00"),
                "stock_quantity": 70,
                "description": "کابل مقاوم USB-C با پشتیبانی از شارژ سریع و انتقال داده.",
                "specifications": {
                    "power_delivery": "100W",
                    "data_speed": "480Mbps",
                    "length_m": 2,
                    "braided": True,
                },
            },
            {
                "name": "Nexora Dock 7-in-1 USB-C Hub",
                "sku": "NX-DOCK-7IN1-001",
                "brand": "Nexora",
                "price": Decimal("4290000.00"),
                "stock_quantity": 21,
                "description": "هاب چندمنظوره برای لپ‌تاپ با خروجی تصویر و کارت‌خوان.",
                "specifications": {
                    "ports": ["HDMI", "USB-A x3", "USB-C PD", "SD", "microSD"],
                    "video": "4K@60Hz",
                    "power_delivery": "100W",
                },
            },
        ],
    },
    "گیمینگ": {
        "slug": "gaming",
        "products": [
            {
                "name": "Nexora Core Gaming Desk Mat",
                "sku": "NX-CORE-MAT-001",
                "brand": "Nexora",
                "price": Decimal("1190000.00"),
                "stock_quantity": 45,
                "description": "پد گیمینگ بزرگ با سطح کنترل و لبه‌های دوخت‌شده.",
                "specifications": {
                    "size_cm": "900 x 400",
                    "surface": "Control fabric",
                    "base": "Anti-slip rubber",
                    "edge": "Stitched",
                },
            },
            {
                "name": "Nexora Shift RGB Controller",
                "sku": "NX-SHIFT-RGB-001",
                "brand": "Nexora",
                "price": Decimal("2890000.00"),
                "stock_quantity": 16,
                "description": "کنترلر بی‌سیم چندسکویی با نورپردازی و اتصال کم‌تأخیر.",
                "specifications": {
                    "platforms": ["PC", "Android", "iOS"],
                    "connection": "Bluetooth, USB-C",
                    "battery_hours": 24,
                    "lighting": "RGB",
                },
            },
        ],
    },
}

EXTRA_CATEGORIES = {
    "کیبورد و ماوس": {
        "children": {
            "کیبورد": [
                ("Nexora Nova Low-Profile Keyboard", "NX-NOVA-KB-001", Decimal("3290000.00"), 24),
                ("Nexora Type-C Compact Keyboard", "NX-TYPEC-KB-001", Decimal("2590000.00"), 31),
            ],
            "ماوس": [
                ("Nexora Glide Ergonomic Mouse", "NX-GLIDE-MOUSE-001", Decimal("1790000.00"), 28),
                ("Nexora Mini Travel Mouse", "NX-MINI-MOUSE-001", Decimal("990000.00"), 40),
                ("Nexora Vector Silent Mouse", "NX-VECTOR-MOUSE-001", Decimal("1490000.00"), 34),
            ],
        },
    },
    "صوتی": {
        "children": {
            "هدفون": [
                ("Nexora Air Mini Earbuds", "NX-AIR-EARBUDS-001", Decimal("2490000.00"), 22),
                ("Nexora Studio Pro Headset", "NX-STUDIO-HEADSET-001", Decimal("5490000.00"), 11),
            ],
            "میکروفون": [
                ("Nexora Beam Streaming Mic", "NX-BEAM-MIC-001", Decimal("2890000.00"), 15),
                ("Nexora Wave Podcast Mic", "NX-WAVE-MIC-001", Decimal("4190000.00"), 12),
            ],
            "اسپیکر": [
                ("Nexora Room Mini Speaker", "NX-ROOM-SPEAKER-001", Decimal("3190000.00"), 19),
            ],
        },
    },
    "گیمینگ": {
        "children": {
            "کنترلر": [
                ("Nexora Edge Wireless Controller", "NX-EDGE-CONTROLLER-001", Decimal("3190000.00"), 18),
                ("Nexora Pocket Gamepad", "NX-POCKET-GAMEPAD-001", Decimal("1890000.00"), 26),
            ],
            "نورپردازی": [
                ("Nexora Glow Desk Light", "NX-GLOW-LIGHT-001", Decimal("1590000.00"), 20),
                ("Nexora Halo Monitor Light", "NX-HALO-LIGHT-001", Decimal("2390000.00"), 17),
            ],
        },
    },
    "کابل و شارژ": {
        "children": {
            "شارژر": [
                ("Nexora Volt GaN Charger 65W", "NX-VOLT-GAN-001", Decimal("2290000.00"), 35),
                ("Nexora Quad USB Charger", "NX-QUAD-CHARGER-001", Decimal("1390000.00"), 42),
                ("Nexora Volt GaN Charger 100W", "NX-VOLT-GAN-100-001", Decimal("3690000.00"), 26),
            ],
            "پاوربانک": [
                ("Nexora Reserve Power Bank 20000", "NX-RESERVE-PB-001", Decimal("2790000.00"), 29),
            ],
        },
    },
}

PRODUCT_IMAGES = {
    "NX-FLUX-KB-001": "products/2026/09/nexora-flux-keyboard.png",
    "NX-ARC-MOUSE-001": "products/2026/09/nexora-arc-mouse.png",
    "NX-PULSE-ANC-001": "products/2026/09/nexora-pulse-headphones.png",
    "NX-ECHO-MIC-001": "products/2026/09/nexora-echo-microphone.png",
}


class Command(BaseCommand):
    help = "Seed the Nexora catalog with realistic demo categories and products."

    @transaction.atomic
    def handle(self, *args, **options):
        category_count = 0
        product_count = 0

        for category_name, category_data in CATALOG.items():
            category, category_created = Category.objects.update_or_create(
                slug=category_data["slug"],
                defaults={
                    "name": category_name,
                    "is_active": True,
                },
            )
            category_count += int(category_created)

            for product_data in category_data["products"]:
                Product.objects.update_or_create(
                    sku=product_data["sku"],
                    defaults={
                        **product_data,
                        "category": category,
                        "image": PRODUCT_IMAGES.get(product_data["sku"], ""),
                        "is_active": True,
                    },
                )
                product_count += 1

            for child_name, child_products in EXTRA_CATEGORIES.get(category_name, {}).get("children", {}).items():
                child_slug = f"{category_data['slug']}-{slugify(child_name, allow_unicode=True)}"
                child, child_created = Category.objects.update_or_create(
                    slug=child_slug,
                    defaults={"name": child_name, "parent": category, "is_active": True},
                )
                category_count += int(child_created)
                for name, sku, price, stock in child_products:
                    Product.objects.update_or_create(
                        sku=sku,
                        defaults={
                            "name": name,
                            "category": child,
                            "brand": "Nexora",
                            "price": price,
                            "stock_quantity": stock,
                            "description": f"{name}؛ محصولی کاربردی برای تجربه بهتر زندگی دیجیتال.",
                            "specifications": {"connection": "USB-C, Bluetooth", "warranty_months": 18},
                            "image": "",
                            "is_active": True,
                        },
                    )
                    product_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Nexora catalog ready: {category_count} new categories, "
                f"{product_count} products synchronized."
            )
        )
