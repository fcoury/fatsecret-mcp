"""Reusable MCP input constraints."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field

PositiveId = Annotated[int, Field(gt=0)]
PositiveAmount = Annotated[Decimal, Field(gt=0)]
NonNegativeMinutes = Annotated[int, Field(ge=0)]
CaloriesPerDay = Annotated[int, Field(ge=500, le=20_000)]
PageNumber = Annotated[int, Field(ge=0)]
MaxResults = Annotated[int, Field(ge=1, le=50)]
IdempotencyKey = Annotated[str, Field(min_length=8, max_length=255)]
ISODate = Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
MealType = Literal["breakfast", "lunch", "dinner", "snack"]
ResolverLimit = Annotated[int, Field(ge=1, le=5)]

__all__ = [
    "CaloriesPerDay",
    "ISODate",
    "IdempotencyKey",
    "MaxResults",
    "MealType",
    "NonNegativeMinutes",
    "PageNumber",
    "PositiveAmount",
    "PositiveId",
    "ResolverLimit",
]
