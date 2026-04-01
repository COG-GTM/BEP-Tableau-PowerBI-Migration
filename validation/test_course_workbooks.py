"""
Validation tests for all 15 course workbook conversions (Sections 5-15).

These tests verify that each converted workbook has the complete set of
Power BI artifacts and that the conversion artifacts are well-formed.
"""

import json
import os
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CONVERSION_DIR = REPO_ROOT / "conversion-output"
TABLEAU_SOURCE = REPO_ROOT / "tableau-source"

# All 15 course workbook output directories
COURSE_WORKBOOKS = [
    "section-05-data-sources",
    "section-06-metadata",
    "section-07-renaming",
    "section-08-organizing-data",
    "section-09-filtering-data",
    "section-10-parameters",
    "section-11-actions",
    "section-12-aggregate-calculations",
    "section-12-lod-expressions",
    "section-12-row-level-calculations",
    "section-12-table-calculations",
    "section-13-multi-measures",
    "section-13-tableau-63-charts",
    "section-14-tableau-dashboard",
    "section-15-sales-customer-dashboards",
]

# Required artifacts for each conversion
REQUIRED_ARTIFACTS = [
    "dax_measures.dax",
    "model.tmdl",
    "layout.json",
    "theme.json",
    "power_query.pq",
    "validation_report.md",
]


class TestCourseWorkbookArtifacts:
    """Verify that all course workbook conversions have complete artifact sets."""

    @pytest.mark.parametrize("workbook", COURSE_WORKBOOKS)
    def test_output_directory_exists(self, workbook: str) -> None:
        """Each workbook must have a conversion output directory."""
        path = CONVERSION_DIR / workbook
        assert path.is_dir(), f"Missing conversion output: {path}"

    @pytest.mark.parametrize("workbook", COURSE_WORKBOOKS)
    @pytest.mark.parametrize("artifact", REQUIRED_ARTIFACTS)
    def test_artifact_exists(self, workbook: str, artifact: str) -> None:
        """Each workbook must contain every required artifact file."""
        path = CONVERSION_DIR / workbook / artifact
        assert path.is_file(), f"Missing artifact: {path}"

    @pytest.mark.parametrize("workbook", COURSE_WORKBOOKS)
    def test_artifact_files_not_empty(self, workbook: str) -> None:
        """All artifact files must have non-zero content."""
        for artifact in REQUIRED_ARTIFACTS:
            path = CONVERSION_DIR / workbook / artifact
            if path.is_file():
                assert path.stat().st_size > 0, f"Empty file: {path}"


class TestDaxMeasures:
    """Validate DAX measure files are well-formed."""

    @pytest.mark.parametrize("workbook", COURSE_WORKBOOKS)
    def test_dax_file_has_content(self, workbook: str) -> None:
        """DAX file should contain measure definitions or a header."""
        path = CONVERSION_DIR / workbook / "dax_measures.dax"
        if path.is_file():
            content = path.read_text(encoding="utf-8")
            assert len(content.strip()) > 0, f"DAX file is empty: {path}"


class TestLayoutJson:
    """Validate layout.json files are valid JSON."""

    @pytest.mark.parametrize("workbook", COURSE_WORKBOOKS)
    def test_layout_is_valid_json(self, workbook: str) -> None:
        """layout.json must be parseable JSON."""
        path = CONVERSION_DIR / workbook / "layout.json"
        if path.is_file():
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            assert isinstance(data, dict), f"layout.json root must be object: {path}"


class TestThemeJson:
    """Validate theme.json files are valid JSON."""

    @pytest.mark.parametrize("workbook", COURSE_WORKBOOKS)
    def test_theme_is_valid_json(self, workbook: str) -> None:
        """theme.json must be parseable JSON."""
        path = CONVERSION_DIR / workbook / "theme.json"
        if path.is_file():
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            assert isinstance(data, dict), f"theme.json root must be object: {path}"


class TestModelTmdl:
    """Validate TMDL model files."""

    @pytest.mark.parametrize("workbook", COURSE_WORKBOOKS)
    def test_tmdl_has_model_declaration(self, workbook: str) -> None:
        """TMDL file should contain a model declaration."""
        path = CONVERSION_DIR / workbook / "model.tmdl"
        if path.is_file():
            content = path.read_text(encoding="utf-8")
            assert "model" in content.lower(), f"TMDL missing model declaration: {path}"


class TestPowerQuery:
    """Validate Power Query M files."""

    @pytest.mark.parametrize("workbook", COURSE_WORKBOOKS)
    def test_power_query_has_content(self, workbook: str) -> None:
        """Power Query file should contain M expressions."""
        path = CONVERSION_DIR / workbook / "power_query.pq"
        if path.is_file():
            content = path.read_text(encoding="utf-8")
            assert len(content.strip()) > 10, f"Power Query file too short: {path}"


class TestValidationReport:
    """Validate that validation reports exist and have content."""

    @pytest.mark.parametrize("workbook", COURSE_WORKBOOKS)
    def test_validation_report_has_content(self, workbook: str) -> None:
        """Validation report should contain results."""
        path = CONVERSION_DIR / workbook / "validation_report.md"
        if path.is_file():
            content = path.read_text(encoding="utf-8")
            assert "PASS" in content or "pass" in content.lower(), (
                f"Validation report missing PASS results: {path}"
            )


class TestBeforeAfterComparison:
    """Validate the BEFORE_AFTER_COMPARISON.md document."""

    def test_comparison_doc_exists(self) -> None:
        """BEFORE_AFTER_COMPARISON.md must exist at repo root."""
        path = REPO_ROOT / "BEFORE_AFTER_COMPARISON.md"
        assert path.is_file(), f"Missing comparison doc: {path}"

    def test_comparison_doc_has_content(self) -> None:
        """Comparison doc must have substantial content."""
        path = REPO_ROOT / "BEFORE_AFTER_COMPARISON.md"
        if path.is_file():
            content = path.read_text(encoding="utf-8")
            assert len(content) > 1000, "Comparison doc too short"
            assert "Migration Summary" in content
            assert "DAX" in content


class TestMigrationTracker:
    """Validate the migration tracker document."""

    def test_tracker_exists(self) -> None:
        """migration_tracker.md must exist."""
        path = CONVERSION_DIR / "migration_tracker.md"
        assert path.is_file(), f"Missing tracker: {path}"

    def test_tracker_covers_all_workbooks(self) -> None:
        """Tracker must reference all 17 workbooks (2 project + 15 course)."""
        path = CONVERSION_DIR / "migration_tracker.md"
        if path.is_file():
            content = path.read_text(encoding="utf-8")
            assert "17" in content, "Tracker should reference 17 total workbooks"
            assert "Complete" in content, "Tracker should show completion status"
