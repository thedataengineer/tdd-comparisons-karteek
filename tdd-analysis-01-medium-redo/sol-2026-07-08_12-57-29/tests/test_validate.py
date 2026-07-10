"""Tests for the validate stage."""

import pytest
from report_pipeline.parse import ParsedRow
from report_pipeline.aggregate import aggregate
from report_pipeline.format import format_table
from report_pipeline.validate import validate_output, ValidationError, _parse_number


def _make_agg(*raw_rows):
    rows = [
        ParsedRow(row_id=i + 1, category=cat, value=val, period=period)
        for i, (cat, val, period) in enumerate(raw_rows)
    ]
    return aggregate(rows)


# ── _parse_number unit tests ──────────────────────────────────────────────────

class TestParseNumber:
    def test_plain_integer(self):
        assert _parse_number("42") == pytest.approx(42.0)

    def test_dollar_amount(self):
        assert _parse_number("$1,234.56") == pytest.approx(1234.56)

    def test_negative_dollar(self):
        assert _parse_number("-$200.00") == pytest.approx(-200.0)

    def test_zero(self):
        assert _parse_number("$0.00") == pytest.approx(0.0)

    def test_empty_string(self):
        assert _parse_number("") == pytest.approx(0.0)

    def test_raises_on_garbage(self):
        with pytest.raises(ValueError):
            _parse_number("$abc")


# ── validate_output: passing cases ───────────────────────────────────────────

class TestValidatePass:
    def _run(self, *raw_rows):
        agg = _make_agg(*raw_rows)
        tbl = format_table(agg)
        return validate_output(tbl, agg), tbl

    def test_returns_table_string_unchanged(self):
        result, tbl = self._run(("REVENUE", 1000.0, "2024-Q1"))
        assert result == tbl

    def test_single_period_single_category(self):
        result, tbl = self._run(("REVENUE", 500.0, "2024-Q1"))
        assert isinstance(result, str)

    def test_multiple_periods(self):
        result, _ = self._run(
            ("REVENUE", 100.0, "2024-Q1"),
            ("REVENUE", 200.0, "2024-Q2"),
        )
        assert isinstance(result, str)

    def test_all_categories(self):
        result, _ = self._run(
            ("REVENUE", 1000.0, "2024-Q1"),
            ("COST", -200.0, "2024-Q1"),
            ("HEADCOUNT", 5.0, "2024-Q1"),
        )
        assert isinstance(result, str)

    def test_negative_cost_row(self):
        result, _ = self._run(("COST", -999.99, "2023-Q4"))
        assert isinstance(result, str)

    def test_headcount_only(self):
        result, _ = self._run(("HEADCOUNT", 100.0, "2024-Q2"))
        assert isinstance(result, str)

    def test_four_periods(self):
        rows = [(f"REVENUE", i * 100.0, f"2024-Q{i}") for i in range(1, 5)]
        result, _ = self._run(*rows)
        assert isinstance(result, str)


# ── validate_output: failing cases ───────────────────────────────────────────

class TestValidateFail:
    def test_missing_period_in_table_string(self):
        agg = _make_agg(("REVENUE", 100.0, "2024-Q1"))
        # Tamper: remove the period from the table
        tbl = format_table(agg).replace("2024-Q1", "XXXX-XX")
        result = validate_output(tbl, agg)
        assert isinstance(result, ValidationError)
        assert result.stage == "validate"
        assert "2024-Q1" in result.reason

    def test_total_mismatch_in_row(self):
        agg = _make_agg(
            ("REVENUE", 100.0, "2024-Q1"),
            ("REVENUE", 200.0, "2024-Q2"),
        )
        tbl = format_table(agg)
        # Corrupt the TOTAL cell value on the REVENUE row
        tbl_corrupted = tbl.replace("$300.00", "$999.00", 1)
        result = validate_output(tbl_corrupted, agg)
        assert isinstance(result, ValidationError)
        assert "TOTAL" in result.reason or "mismatch" in result.reason.lower()

    def test_column_narrower_than_header_detected(self):
        """Simulate a column_width < header_length by injecting a bad layout."""
        agg = _make_agg(("REVENUE", 1.0, "2024-Q1"))
        tbl = format_table(agg)
        # Monkeypatch compute_layout to return a too-small width
        import report_pipeline.validate as vmod
        orig = vmod.compute_layout

        def bad_layout(agg):
            lw, ck, cw = orig(agg)
            # Make the first column width smaller than header
            first_col = ck[0]
            cw[first_col] = 1  # definitely narrower than "2024-Q1" (7 chars)
            return lw, ck, cw

        vmod.compute_layout = bad_layout
        try:
            result = validate_output(tbl, agg)
        finally:
            vmod.compute_layout = orig

        assert isinstance(result, ValidationError)
        assert "narrower" in result.reason.lower()

    def test_validation_error_has_stage_attribute(self):
        agg = _make_agg(("REVENUE", 100.0, "2024-Q1"))
        tbl = format_table(agg).replace("2024-Q1", "XXXX-XX")
        err = validate_output(tbl, agg)
        assert isinstance(err, ValidationError)
        assert err.stage == "validate"

    def test_period_missing_from_col_keys(self):
        """Period appears in aggregated.periods but not in compute_layout col_keys."""
        agg = _make_agg(("REVENUE", 100.0, "2024-Q1"))
        tbl = format_table(agg)
        import report_pipeline.validate as vmod
        orig = vmod.compute_layout

        def bad_layout(agg):
            lw, ck, cw = orig(agg)
            return lw, [], cw  # empty col_keys

        vmod.compute_layout = bad_layout
        try:
            result = validate_output(tbl, agg)
        finally:
            vmod.compute_layout = orig

        assert isinstance(result, ValidationError)
        assert "missing from table columns" in result.reason

    def test_negative_label_width_detected(self):
        """Negative label_width is caught."""
        agg = _make_agg(("REVENUE", 100.0, "2024-Q1"))
        tbl = format_table(agg)
        import report_pipeline.validate as vmod
        orig = vmod.compute_layout

        def bad_layout(agg):
            lw, ck, cw = orig(agg)
            return -1, ck, cw

        vmod.compute_layout = bad_layout
        try:
            result = validate_output(tbl, agg)
        finally:
            vmod.compute_layout = orig

        assert isinstance(result, ValidationError)
        assert "negative" in result.reason.lower()

    def test_extract_cells_exception_caught(self):
        """If _extract_cells raises, a ValidationError is returned."""
        agg = _make_agg(("REVENUE", 100.0, "2024-Q1"))
        tbl = format_table(agg)
        import report_pipeline.validate as vmod
        orig = vmod._extract_cells

        def bad_extract(*args, **kwargs):
            raise RuntimeError("simulated extraction failure")

        vmod._extract_cells = bad_extract
        try:
            result = validate_output(tbl, agg)
        finally:
            vmod._extract_cells = orig

        assert isinstance(result, ValidationError)
        assert "Could not extract cells" in result.reason

    def test_parse_number_exception_caught(self):
        """If _parse_number raises, a ValidationError is returned."""
        agg = _make_agg(("REVENUE", 100.0, "2024-Q1"))
        tbl = format_table(agg)
        import report_pipeline.validate as vmod
        orig = vmod._parse_number
        call_count = [0]

        def bad_parse(s):
            call_count[0] += 1
            if call_count[0] > 1:
                raise ValueError("simulated parse failure")
            return orig(s)

        vmod._parse_number = bad_parse
        try:
            result = validate_output(tbl, agg)
        finally:
            vmod._parse_number = orig

        assert isinstance(result, ValidationError)
        assert "Could not parse" in result.reason
