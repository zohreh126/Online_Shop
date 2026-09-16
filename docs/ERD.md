# Nexora ERD

این نمودار رابطه‌ی مدل‌های اصلی پروژه را نشان می‌دهد و در GitHub قابل مشاهده است.

```mermaid
erDiagram
    CUSTOMER ||--o{ ADDRESS : has
    CUSTOMER ||--o{ CART : owns
    CUSTOMER ||--o{ ORDER : places
    CUSTOMER ||--o{ REWARD_TRANSACTION : earns
    CATEGORY ||--o{ CATEGORY : contains
    CATEGORY ||--o{ PRODUCT : classifies
    PRODUCT ||--o| DISCOUNT : has
    DISCOUNT_CODE ||--o{ CART : applied_to
    DISCOUNT_CODE ||--o{ ORDER : applied_to
    CART ||--o{ CART_ITEM : contains
    PRODUCT ||--o{ CART_ITEM : selected
    ORDER ||--o{ ORDER_ITEM : contains
    ORDER ||--o| REWARD_TRANSACTION : grants
    PRODUCT ||--o{ ORDER_ITEM : snapshot_source

    CUSTOMER {
        bigint id PK
        string username UK
        string email UK
        string role
        boolean is_active
        boolean email_verified
    }
    ADDRESS {
        bigint id PK
        bigint customer_id FK
        string province
        string city
        string postal_code
        boolean is_default
        boolean is_active
    }
    CATEGORY {
        bigint id PK
        bigint parent_id FK
        string name
        string slug UK
        boolean is_active
    }
    PRODUCT {
        bigint id PK
        bigint category_id FK
        string sku UK
        decimal price
        integer stock_quantity
        boolean is_active
    }
    DISCOUNT {
        bigint id PK
        bigint product_id FK
        string discount_type
        decimal value
        decimal max_amount
        boolean is_active
    }
    DISCOUNT_CODE {
        bigint id PK
        string code UK
        string discount_type
        decimal value
        integer usage_limit
        integer used_count
        boolean is_active
    }
    CART {
        bigint id PK
        bigint customer_id FK
        string session_key UK
        bigint discount_code_id FK
        boolean is_active
    }
    CART_ITEM {
        bigint id PK
        bigint cart_id FK
        bigint product_id FK
        integer quantity
    }
    ORDER {
        bigint id PK
        uuid order_number UK
        bigint customer_id FK
        string status
        string payment_status
        decimal total_amount
        string shipping_address_line
    }
    ORDER_ITEM {
        bigint id PK
        bigint order_id FK
        bigint product_id FK
        string product_name
        string product_sku
        decimal unit_price
        decimal unit_discount
        integer quantity
        decimal line_total
    }
    REWARD_TRANSACTION {
        bigint id PK
        bigint customer_id FK
        bigint order_id UK FK
        integer points
        string reason
    }
```

`ORDER_ITEM` نام، SKU، قیمت و تخفیف محصول را snapshot می‌کند تا تاریخچه‌ی سفارش با تغییر محصول از بین نرود.
`REWARD_TRANSACTION` نیز یک دفتر immutable برای امتیاز سفارش‌های پرداخت‌شده است؛ هر سفارش حداکثر یک تراکنش امتیاز دارد.
