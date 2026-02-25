from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


EstadoFinal = Literal[
    "synced_to_fatsecret",
    "captured_pending_sync",
    "captured_pending_review",
    "failed_not_captured",
]


class SobreApi(BaseModel):
    ok: bool
    phase: str
    data: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class SolicitudTextoReferencia(BaseModel):
    text: str
    reference_date: str | None = None


class SolicitudResolver(BaseModel):
    text: str | None = None
    reference_date: str | None = None
    intencion_normalizada: dict[str, Any] | None = None


class SolicitudExecute(BaseModel):
    plan: dict[str, Any]


class OperacionParseada(BaseModel):
    op: str
    target: str | None = None


class SalidaParserLLM(BaseModel):
    intent: str
    date_ref: str | None = None
    meal_hint: str | None = None
    combo_ref: str | None = None
    food_ref: str | None = None
    grams: float | None = None
    operations: list[OperacionParseada] = Field(default_factory=list)


class OperacionNormalizada(BaseModel):
    op: str
    target_raw: str
    target_normalized: str


class IntencionNormalizada(BaseModel):
    intent: str
    date: str | None = None
    meal_type: str | None = None
    combo_ref_raw: str | None = None
    combo_ref_normalized: str | None = None
    food_ref_raw: str | None = None
    food_ref_normalized: str | None = None
    grams: float | None = None
    operations: list[OperacionNormalizada] = Field(default_factory=list)
    parser_valid: bool = True
    parse_issues: list[dict[str, Any]] = Field(default_factory=list)


class SolicitudParseAndLog(BaseModel):
    text: str
    reference_date: str | None = None
    ejecutar_escritura: bool = True


class ResultadoEjecucion(BaseModel):
    status: str
    date: str
    meal_type: str
    executed_count: int
    failed_count: int
    entries: list[dict[str, Any]] = Field(default_factory=list)
    partial_failures: list[dict[str, Any]] = Field(default_factory=list)

