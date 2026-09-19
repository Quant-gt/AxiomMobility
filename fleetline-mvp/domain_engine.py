"""Deterministic paise-exact duty calculation engine for Axiom Fleet.

All monetary inputs and outputs are integer paise. Rates are expressed in
paise, durations in minutes and tax as basis points (18% = 1800).
"""

from __future__ import annotations

from dataclasses import dataclass


class CalculationError(ValueError):
    pass


def _non_negative_int(value: object, name: str) -> int:
    if value in (None, ""):
        return 0
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise CalculationError(f"{name} must be an integer") from exc
    if number < 0:
        raise CalculationError(f"{name} cannot be negative")
    return number


def round_div(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        raise CalculationError("denominator must be positive")
    return (numerator + denominator // 2) // denominator


@dataclass(frozen=True)
class DutyInputs:
    base_paise: int = 0
    distance_km: int = 0
    per_km_paise: int = 0
    duration_minutes: int = 0
    per_hour_paise: int = 0
    waiting_minutes: int = 0
    waiting_paise: int = 0
    toll_paise: int = 0
    parking_paise: int = 0
    expense_paise: int = 0
    tax_rate_bps: int = 0

    @classmethod
    def from_payload(cls, payload: dict) -> "DutyInputs":
        values = {field: _non_negative_int(payload.get(field), field) for field in cls.__dataclass_fields__}
        if values["tax_rate_bps"] > 10_000:
            raise CalculationError("tax_rate_bps cannot exceed 10000")
        return cls(**values)


def calculate_duty(payload: dict) -> dict:
    """Return explainable line items and totals for one duty.

    Hourly and waiting rates are prorated by minutes and rounded half-up at
    the line level. Tax is rounded half-up after subtotal calculation.
    """
    inputs = DutyInputs.from_payload(payload)
    lines = []

    def add_line(code: str, label: str, quantity: int, unit_paise: int, amount_paise: int, source: str) -> None:
        if amount_paise:
            lines.append({
                "code": code,
                "label": label,
                "quantity": quantity,
                "unit_paise": unit_paise,
                "amount_paise": amount_paise,
                "source": source,
            })

    add_line("base", "Base duty", 1, inputs.base_paise, inputs.base_paise, "price_book")
    km_amount = inputs.distance_km * inputs.per_km_paise
    add_line("distance", "Distance", inputs.distance_km, inputs.per_km_paise, km_amount, "odometer")
    time_amount = round_div(inputs.duration_minutes * inputs.per_hour_paise, 60)
    add_line("time", "Time", inputs.duration_minutes, inputs.per_hour_paise, time_amount, "duty_clock")
    waiting_amount = round_div(inputs.waiting_minutes * inputs.waiting_paise, 60)
    add_line("waiting", "Waiting", inputs.waiting_minutes, inputs.waiting_paise, waiting_amount, "duty_clock")
    add_line("toll", "Toll", 1, inputs.toll_paise, inputs.toll_paise, "expense")
    add_line("parking", "Parking", 1, inputs.parking_paise, inputs.parking_paise, "expense")
    add_line("expense", "Other expense", 1, inputs.expense_paise, inputs.expense_paise, "expense")

    subtotal_paise = sum(line["amount_paise"] for line in lines)
    tax_paise = round_div(subtotal_paise * inputs.tax_rate_bps, 10_000)
    total_paise = subtotal_paise + tax_paise
    return {
        "engine_version": "2026.09.1",
        "inputs": inputs.__dict__,
        "lines": lines,
        "subtotal_paise": subtotal_paise,
        "tax_rate_bps": inputs.tax_rate_bps,
        "tax_paise": tax_paise,
        "total_paise": total_paise,
    }
