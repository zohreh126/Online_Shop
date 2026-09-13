from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

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

        self.stdout.write(
            self.style.SUCCESS(
                f"Nexora catalog ready: {category_count} new categories, "
                f"{product_count} products synchronized."
            )
        )
