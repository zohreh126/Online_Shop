from rest_framework.pagination import PageNumberPagination


class NexoraPagination(PageNumberPagination):
    """Pagination shared by catalog endpoints consumed by the storefront."""

    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 100
