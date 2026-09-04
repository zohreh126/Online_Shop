from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from core.models import TimeStampedModel


class Category(TimeStampedModel):
    name = models.CharField(
        max_length=150,
    )

    slug = models.SlugField(
        max_length=180,
        unique=True,
        allow_unicode=True,
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ("name",)
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        constraints = [
            models.UniqueConstraint(
                fields=("parent", "name"),
                name="unique_category_name_per_parent",
            ),
        ]

    def clean(self):
        super().clean()

        if self.parent_id == self.pk:
            raise ValidationError(
                {"parent": "A category cannot be its own parent."}
            )

        ancestor = self.parent
        visited_ids = set()

        while ancestor:
            if ancestor.pk in visited_ids:
                break

            if ancestor.pk == self.pk:
                raise ValidationError(
                    {"parent": "Circular category relationship is not allowed."}
                )

            visited_ids.add(ancestor.pk)
            ancestor = ancestor.parent

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(
                self.name,
                allow_unicode=True,
            )

        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name
