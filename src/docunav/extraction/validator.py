"""Extraction validation engine.

Runs rule-based checks against an Extraction to catch errors
before output is trusted.
"""

from __future__ import annotations

from typing import Any

from docunav.models.document import (
    DocumentGraph,
    Extraction,
    ValidationResult,
    ValidationSeverity,
)
from docunav.extraction.schemas import ExtractionSchema, SchemaRegistry


class Validator:
    """Validates an extraction result."""

    def __init__(self, schema_registry: SchemaRegistry | None = None) -> None:
        self.registry = schema_registry or SchemaRegistry()

    def validate(
        self,
        extraction: Extraction,
        graph: DocumentGraph | None = None,
    ) -> list[ValidationResult]:
        results: list[ValidationResult] = []

        schema = None
        if extraction.schema_id and self.registry:
            schema = self.registry.get(extraction.schema_id)

        # 1. Schema validation — required fields
        if schema:
            results.extend(self._check_required_fields(extraction, schema))
            results.extend(self._check_field_types(extraction, schema))

        # 2. Citation validation
        results.extend(self._check_citations(extraction))

        # 3. Confidence validation
        results.extend(self._check_confidence(extraction))

        # 4. Domain-specific validation
        if extraction.schema_id == "invoice":
            results.extend(self._validate_invoice(extraction))

        return results

    def _check_required_fields(
        self, extraction: Extraction, schema: ExtractionSchema
    ) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        extracted_fields = {f.field_path for f in extraction.fields}

        for field_def in schema.fields:
            if field_def.required and field_def.name not in extracted_fields:
                results.append(ValidationResult(
                    extraction_id=extraction.id,
                    severity=ValidationSeverity.ERROR,
                    rule_name="required_field_missing",
                    message=f"Required field '{field_def.name}' is missing.",
                    affected_fields=[field_def.name],
                ))
            elif field_def.required:
                field = next(
                    (f for f in extraction.fields if f.field_path == field_def.name), None
                )
                if field and field.value is None:
                    results.append(ValidationResult(
                        extraction_id=extraction.id,
                        severity=ValidationSeverity.ERROR,
                        rule_name="required_field_null",
                        message=f"Required field '{field_def.name}' has no value.",
                        affected_fields=[field_def.name],
                    ))

        return results

    def _check_field_types(
        self, extraction: Extraction, schema: ExtractionSchema
    ) -> list[ValidationResult]:
        results: list[ValidationResult] = []

        schema_fields = {f.name: f for f in schema.fields}
        for field in extraction.fields:
            if field.value is None:
                continue
            fd = schema_fields.get(field.field_path)
            if not fd:
                continue

            if fd.field_type in ("number", "currency", "integer"):
                if not isinstance(field.value, (int, float)):
                    try:
                        float(str(field.value).replace(",", "").replace("$", "").replace("€", ""))
                    except (ValueError, TypeError):
                        results.append(ValidationResult(
                            extraction_id=extraction.id,
                            severity=ValidationSeverity.WARNING,
                            rule_name="type_mismatch",
                            message=f"Field '{field.field_path}' expected numeric but got '{type(field.value).__name__}'.",
                            affected_fields=[field.field_path],
                        ))

        return results

    def _check_citations(self, extraction: Extraction) -> list[ValidationResult]:
        results: list[ValidationResult] = []

        for field in extraction.fields:
            if field.value is not None and not field.citations:
                results.append(ValidationResult(
                    extraction_id=extraction.id,
                    severity=ValidationSeverity.WARNING,
                    rule_name="missing_citation",
                    message=f"Field '{field.field_path}' has a value but no source citation.",
                    affected_fields=[field.field_path],
                ))

        return results

    def _check_confidence(self, extraction: Extraction) -> list[ValidationResult]:
        results: list[ValidationResult] = []

        for field in extraction.fields:
            if field.value is not None and field.confidence < 0.5:
                results.append(ValidationResult(
                    extraction_id=extraction.id,
                    severity=ValidationSeverity.WARNING,
                    rule_name="low_confidence",
                    message=f"Field '{field.field_path}' has low confidence ({field.confidence:.2f}). Recommend human review.",
                    affected_fields=[field.field_path],
                ))

        return results

    def _validate_invoice(self, extraction: Extraction) -> list[ValidationResult]:
        """Invoice-specific arithmetic validation."""
        results: list[ValidationResult] = []

        field_map = {f.field_path: f for f in extraction.fields}
        subtotal_f = field_map.get("subtotal")
        tax_f = field_map.get("tax")
        total_f = field_map.get("total")

        if subtotal_f and total_f and subtotal_f.value is not None and total_f.value is not None:
            try:
                subtotal = float(subtotal_f.value)
                total = float(total_f.value)
                tax = float(tax_f.value) if tax_f and tax_f.value is not None else 0.0

                expected = subtotal + tax
                if abs(expected - total) > 0.01:
                    results.append(ValidationResult(
                        extraction_id=extraction.id,
                        severity=ValidationSeverity.ERROR,
                        rule_name="arithmetic_mismatch",
                        message=(
                            f"Total ({total}) does not equal subtotal ({subtotal}) + tax ({tax}) = {expected}."
                        ),
                        affected_fields=["subtotal", "tax", "total"],
                    ))
                else:
                    results.append(ValidationResult(
                        extraction_id=extraction.id,
                        severity=ValidationSeverity.INFO,
                        rule_name="arithmetic_valid",
                        message="Total matches subtotal + tax.",
                        affected_fields=["subtotal", "tax", "total"],
                        status="passed",
                    ))
            except (ValueError, TypeError):
                results.append(ValidationResult(
                    extraction_id=extraction.id,
                    severity=ValidationSeverity.WARNING,
                    rule_name="arithmetic_check_skipped",
                    message="Could not perform arithmetic validation — non-numeric values.",
                    affected_fields=["subtotal", "tax", "total"],
                ))

        return results
