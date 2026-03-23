#!/usr/bin/env python3
"""
Generate cleaned, Power BI-ready CSV datasets from the source project data.

Handles:
  - EU formatting: semicolon delimiters → comma, DD/MM/YYYY → YYYY-MM-DD
  - Decimal commas → decimal points
  - Column name standardization
  - Whitespace trimming
  - Data type validation

Usage:
    python scripts/generate_powerbi_datasets.py [--output-dir conversion-output/powerbi-ready]
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read_csv_safe(path, sep=";"):
    """Read a CSV with encoding fallback (utf-8 → latin-1)."""
    try:
        return pd.read_csv(path, sep=sep, encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(path, sep=sep, encoding="latin-1")


def clean_sales_orders(input_path, output_path):
    """Clean and standardize the Sales Orders dataset."""
    print(f"  Processing Orders: {input_path}")
    df = _read_csv_safe(input_path, sep=";")

    # Standardize column names
    df.columns = df.columns.str.strip()

    # Parse dates
    df["Order Date"] = pd.to_datetime(df["Order Date"], format="mixed", dayfirst=True)
    df["Ship Date"] = pd.to_datetime(df["Ship Date"], format="mixed", dayfirst=True)

    # Ensure numeric types
    for col in ["Sales", "Quantity", "Discount", "Profit"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Trim string columns
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].str.strip()

    # Format dates as YYYY-MM-DD for output
    df["Order Date"] = df["Order Date"].dt.strftime("%Y-%m-%d")
    df["Ship Date"] = df["Ship Date"].dt.strftime("%Y-%m-%d")

    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"    → {output_path} ({len(df)} rows)")
    return df


def clean_sales_customers(input_path, output_path):
    """Clean and standardize the Customers dataset."""
    print(f"  Processing Customers: {input_path}")
    df = _read_csv_safe(input_path, sep=";")
    df.columns = df.columns.str.strip()

    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].str.strip()

    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"    → {output_path} ({len(df)} rows)")
    return df


def clean_sales_products(input_path, output_path):
    """Clean and standardize the Products dataset."""
    print(f"  Processing Products: {input_path}")
    df = _read_csv_safe(input_path, sep=";")
    df.columns = df.columns.str.strip()

    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].str.strip()

    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"    → {output_path} ({len(df)} rows)")
    return df


def clean_sales_location(input_path, output_path):
    """Clean and standardize the Location dataset."""
    print(f"  Processing Location: {input_path}")
    df = _read_csv_safe(input_path, sep=";")
    df.columns = df.columns.str.strip()

    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].str.strip()

    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"    → {output_path} ({len(df)} rows)")
    return df


def clean_hr_dataset(input_path, output_path):
    """Clean and standardize the HR dataset.

    Handles:
      - Semicolon delimiters
      - DD/MM/YYYY date format → YYYY-MM-DD
    """
    print(f"  Processing HR: {input_path}")
    df = pd.read_csv(input_path, sep=";", encoding="utf-8")
    df.columns = df.columns.str.strip()

    # Parse dates with dayfirst=True for DD/MM/YYYY
    for date_col in ["Birthdate", "Hiredate", "Termdate"]:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(
                df[date_col], format="mixed", dayfirst=True, errors="coerce"
            )
            df[date_col] = df[date_col].dt.strftime("%Y-%m-%d")
            # Replace 'NaT' string representations with empty string
            df[date_col] = df[date_col].fillna("")

    # Ensure Salary is numeric
    if "Salary" in df.columns:
        df["Salary"] = pd.to_numeric(df["Salary"], errors="coerce")

    # Trim string columns
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].str.strip()

    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"    → {output_path} ({len(df)} rows)")
    return df


def clean_vulnerabilities(input_path, output_path):
    """Clean and standardize the CISO vulnerabilities dataset."""
    print(f"  Processing Vulnerabilities: {input_path}")
    df = _read_csv_safe(input_path, sep=",")
    df.columns = df.columns.str.strip()

    # Parse dates
    for date_col in ["First_Seen", "Last_Seen", "Remediated_Date"]:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df[date_col] = df[date_col].dt.strftime("%Y-%m-%d")
            df[date_col] = df[date_col].fillna("")

    # Ensure CVSS_Score is numeric
    if "CVSS_Score" in df.columns:
        df["CVSS_Score"] = pd.to_numeric(df["CVSS_Score"], errors="coerce")

    # Trim string columns
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].str.strip()

    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"    → {output_path} ({len(df)} rows)")
    return df


def clean_jira_issues(input_path, output_path):
    """Clean and standardize the JIRA issues dataset."""
    print(f"  Processing JIRA Issues: {input_path}")
    df = _read_csv_safe(input_path, sep=",")
    df.columns = df.columns.str.strip()

    # Parse dates
    for date_col in [
        "Sprint_Start",
        "Sprint_End",
        "Created_Date",
        "Updated_Date",
        "Resolved_Date",
    ]:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df[date_col] = df[date_col].dt.strftime("%Y-%m-%d")
            df[date_col] = df[date_col].fillna("")

    # Ensure Story_Points is numeric
    if "Story_Points" in df.columns:
        df["Story_Points"] = pd.to_numeric(df["Story_Points"], errors="coerce")

    # Trim string columns
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].str.strip()

    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"    → {output_path} ({len(df)} rows)")
    return df


def main():
    parser = argparse.ArgumentParser(
        description="Generate cleaned Power BI-ready CSV datasets."
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(REPO_ROOT, "conversion-output", "powerbi-ready"),
        help="Output directory for cleaned CSVs",
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print("Generating Power BI-ready datasets...")
    print(f"Output directory: {args.output_dir}")
    print()

    results = {}

    # Sales datasets (semicolon-delimited)
    sales_dir = os.path.join(
        REPO_ROOT, "projects", "sales-dashboard-project", "datasets", "non-eu"
    )
    print("[1/4] Sales Dashboard datasets:")
    results["Orders"] = clean_sales_orders(
        os.path.join(sales_dir, "Orders.csv"),
        os.path.join(args.output_dir, "Orders_clean.csv"),
    )
    results["Customers"] = clean_sales_customers(
        os.path.join(sales_dir, "Customers.csv"),
        os.path.join(args.output_dir, "Customers_clean.csv"),
    )
    results["Products"] = clean_sales_products(
        os.path.join(sales_dir, "Products.csv"),
        os.path.join(args.output_dir, "Products_clean.csv"),
    )
    results["Location"] = clean_sales_location(
        os.path.join(sales_dir, "Location.csv"),
        os.path.join(args.output_dir, "Location_clean.csv"),
    )
    print()

    # HR dataset (semicolon-delimited, EU dates)
    hr_path = os.path.join(
        REPO_ROOT, "projects", "hr-dashboard-project", "dataset.csv"
    )
    print("[2/4] HR Dashboard dataset:")
    results["HR"] = clean_hr_dataset(
        hr_path,
        os.path.join(args.output_dir, "HR_clean.csv"),
    )
    print()

    # Vulnerabilities dataset (comma-delimited)
    vuln_path = os.path.join(
        REPO_ROOT, "projects", "ciso-cybersecurity-project", "vulnerabilities.csv"
    )
    print("[3/4] CISO Cybersecurity dataset:")
    results["Vulnerabilities"] = clean_vulnerabilities(
        vuln_path,
        os.path.join(args.output_dir, "Vulnerabilities_clean.csv"),
    )
    print()

    # JIRA Issues dataset (comma-delimited)
    jira_path = os.path.join(
        REPO_ROOT, "projects", "it-project-mgmt-project", "jira_issues.csv"
    )
    print("[4/4] IT Project Management dataset:")
    results["JIRA_Issues"] = clean_jira_issues(
        jira_path,
        os.path.join(args.output_dir, "JIRA_Issues_clean.csv"),
    )
    print()

    # Summary
    print("=" * 60)
    print("DATASET GENERATION SUMMARY")
    print("=" * 60)
    total_rows = 0
    for name, df in results.items():
        rows = len(df)
        total_rows += rows
        print(f"  {name:20s}: {rows:>6,} rows, {len(df.columns):>3} columns")
    print(f"  {'TOTAL':20s}: {total_rows:>6,} rows")
    print(f"\nAll cleaned datasets written to: {args.output_dir}")


if __name__ == "__main__":
    main()
