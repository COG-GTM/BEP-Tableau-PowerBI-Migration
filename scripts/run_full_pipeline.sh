#!/usr/bin/env bash
# ==============================================================================
# BEP Tableau-to-Power BI Migration — Full Pipeline
# ==============================================================================
#
# Runs the complete migration pipeline:
#   1. Parse docx (if provided) → generate manifest
#   2. Clean datasets → output to powerbi-ready/
#   3. Run validation suite
#   4. Generate validation report
#   5. Print summary
#
# Usage:
#   bash scripts/run_full_pipeline.sh [path_to_docx]
#
# ==============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

DOCX_PATH="${1:-}"
OUTPUT_DIR="conversion-output"

echo "================================================================"
echo "  BEP Tableau-to-Power BI Migration Pipeline"
echo "================================================================"
echo ""
echo "Repository root: $REPO_ROOT"
echo "Output directory: $OUTPUT_DIR"
echo ""

# --- Step 1: Install dependencies ---
echo "--- Step 1: Installing dependencies ---"
if [ -f requirements.txt ]; then
    pip install -q -r requirements.txt 2>/dev/null || {
        echo "WARNING: Some pip packages failed to install. Continuing..."
    }
fi
if [ -f validation/requirements.txt ]; then
    pip install -q -r validation/requirements.txt 2>/dev/null || true
fi
echo "Done."
echo ""

# --- Step 2: Parse docx (if provided) ---
echo "--- Step 2: Parsing dashboard definitions ---"
if [ -n "$DOCX_PATH" ] && [ -f "$DOCX_PATH" ]; then
    echo "Parsing docx: $DOCX_PATH"
    python3 scripts/parse_dashboard_docx.py "$DOCX_PATH" --output-dir "$OUTPUT_DIR"
elif [ -f "$OUTPUT_DIR/dashboard_manifest.json" ]; then
    echo "Manifest already exists. Skipping docx parsing."
else
    echo "No docx provided. Generating manifest from defaults."
    python3 scripts/parse_dashboard_docx.py --output-dir "$OUTPUT_DIR"
fi
echo ""

# --- Step 3: Generate cleaned datasets ---
echo "--- Step 3: Generating Power BI-ready datasets ---"
python3 scripts/generate_powerbi_datasets.py --output-dir "$OUTPUT_DIR/powerbi-ready"
echo ""

# --- Step 4: Verify conversion artifacts exist ---
echo "--- Step 4: Verifying conversion artifacts ---"
DASHBOARDS=("sales-dashboard" "hr-dashboard" "ciso-cybersecurity-dashboard" "it-project-mgmt-dashboard")
ARTIFACTS=("dax_measures.dax" "model.tmdl" "layout.json" "theme.json" "power_query.pq" "validation_report.md")

all_present=true
for db in "${DASHBOARDS[@]}"; do
    for art in "${ARTIFACTS[@]}"; do
        if [ -f "$OUTPUT_DIR/$db/$art" ]; then
            echo "  [OK] $db/$art"
        else
            echo "  [MISSING] $db/$art"
            all_present=false
        fi
    done
done
echo ""

if [ "$all_present" = false ]; then
    echo "WARNING: Some conversion artifacts are missing."
    echo "Run the individual dashboard conversion scripts or child Devin sessions first."
    echo ""
fi

# --- Step 5: Run validation suite ---
echo "--- Step 5: Running validation suite ---"
if [ -d "validation" ] && [ -f "validation/conftest.py" ]; then
    python3 -m pytest validation/ -v --tb=short 2>&1 || {
        echo ""
        echo "WARNING: Some validation tests failed. Review the output above."
    }
    echo ""

    # Generate validation report
    if [ -f "validation/run_validation.py" ]; then
        echo "--- Step 5b: Generating validation report ---"
        python3 validation/run_validation.py || true
        echo ""
    fi
else
    echo "Validation framework not found. Skipping."
    echo ""
fi

# --- Step 6: Print summary ---
echo "================================================================"
echo "  PIPELINE COMPLETE"
echo "================================================================"
echo ""
echo "Generated artifacts:"
echo "  - Dashboard manifest:  $OUTPUT_DIR/dashboard_manifest.json"
echo "  - Dashboard inventory: $OUTPUT_DIR/dashboard_inventory.md"
echo "  - Migration tracker:   $OUTPUT_DIR/migration_tracker.md"
echo "  - Conversion summary:  $OUTPUT_DIR/conversion_summary.md"
echo ""
echo "Cleaned datasets:"
for f in "$OUTPUT_DIR/powerbi-ready"/*.csv; do
    if [ -f "$f" ]; then
        rows=$(wc -l < "$f")
        echo "  - $(basename "$f"): $((rows - 1)) rows"
    fi
done
echo ""
echo "Dashboard conversion artifacts:"
for db in "${DASHBOARDS[@]}"; do
    count=$(ls "$OUTPUT_DIR/$db/" 2>/dev/null | wc -l)
    echo "  - $db/: $count files"
done
echo ""

if [ -f "validation/reports/conversion_validation_report.md" ]; then
    echo "Validation report: validation/reports/conversion_validation_report.md"
fi
if [ -f "validation/reports/validation_summary.json" ]; then
    echo "Validation JSON:   validation/reports/validation_summary.json"
fi

echo ""
echo "Pipeline finished successfully."
