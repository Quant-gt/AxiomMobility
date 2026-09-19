#!/usr/bin/env python3
"""Generated 1,000-case golden/invariant suite for the paise duty engine."""

from __future__ import annotations

import random

from domain_engine import calculate_duty, round_div


def main() -> None:
    rng = random.Random(20260919)
    cases = 1000
    for index in range(cases):
        payload = {
            "base_paise": rng.randrange(0, 250_000, 25),
            "distance_km": rng.randrange(0, 800),
            "per_km_paise": rng.randrange(0, 7_500, 25),
            "duration_minutes": rng.randrange(0, 1_440),
            "per_hour_paise": rng.randrange(0, 12_000, 25),
            "waiting_minutes": rng.randrange(0, 360),
            "waiting_paise": rng.randrange(0, 6_000, 25),
            "toll_paise": rng.randrange(0, 25_000, 25),
            "parking_paise": rng.randrange(0, 12_000, 25),
            "expense_paise": rng.randrange(0, 30_000, 25),
            "tax_rate_bps": rng.randrange(0, 2_801),
        }
        result = calculate_duty(payload)
        expected_lines = [
            payload["base_paise"],
            payload["distance_km"] * payload["per_km_paise"],
            round_div(payload["duration_minutes"] * payload["per_hour_paise"], 60),
            round_div(payload["waiting_minutes"] * payload["waiting_paise"], 60),
            payload["toll_paise"],
            payload["parking_paise"],
            payload["expense_paise"],
        ]
        subtotal = sum(expected_lines)
        tax = round_div(subtotal * payload["tax_rate_bps"], 10_000)
        assert result["subtotal_paise"] == subtotal, f"case {index}: subtotal"
        assert result["tax_paise"] == tax, f"case {index}: tax"
        assert result["total_paise"] == subtotal + tax, f"case {index}: total"
        assert sum(line["amount_paise"] for line in result["lines"]) == subtotal, f"case {index}: explainability"
        assert result["engine_version"] == "2026.09.1", f"case {index}: version"
    print(f"PASS generated golden calculation suite: {cases}/{cases} cases")


if __name__ == "__main__":
    main()
