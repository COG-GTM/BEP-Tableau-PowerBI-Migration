"""
Shared pytest fixtures for BEP Tableau-to-Power BI validation tests.

Loads each dataset once per test session with proper parsing
(delimiters, date formats) for efficiency.
"""

import os

import pandas as pd
import pytest

# Base path for all project datasets
BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "projects",
)


@pytest.fixture(scope="session")
def sales_orders_df() -> pd.DataFrame:
    """Load Sales Dashboard Orders with semicolon delimiter and date parsing."""
    path = os.path.join(
        BASE_DIR, "sales-dashboard-project", "datasets", "non-eu", "Orders.csv"
    )
    df = pd.read_csv(path, sep=";")
    # Dates are DD/MM/YYYY — parse explicitly after loading
    df["Order Date"] = pd.to_datetime(df["Order Date"], dayfirst=True)
    df["Ship Date"] = pd.to_datetime(df["Ship Date"], dayfirst=True)
    return df


@pytest.fixture(scope="session")
def sales_customers_df() -> pd.DataFrame:
    """Load Sales Dashboard Customers with semicolon delimiter."""
    path = os.path.join(
        BASE_DIR, "sales-dashboard-project", "datasets", "non-eu", "Customers.csv"
    )
    return pd.read_csv(path, sep=";")


@pytest.fixture(scope="session")
def sales_products_df() -> pd.DataFrame:
    """Load Sales Dashboard Products with semicolon delimiter."""
    path = os.path.join(
        BASE_DIR, "sales-dashboard-project", "datasets", "non-eu", "Products.csv"
    )
    return pd.read_csv(path, sep=";")


@pytest.fixture(scope="session")
def sales_location_df() -> pd.DataFrame:
    """Load Sales Dashboard Location with semicolon delimiter."""
    path = os.path.join(
        BASE_DIR, "sales-dashboard-project", "datasets", "non-eu", "Location.csv"
    )
    return pd.read_csv(path, sep=";")


@pytest.fixture(scope="session")
def hr_df() -> pd.DataFrame:
    """Load HR Dashboard dataset with semicolon delimiter and DD/MM/YYYY dates."""
    path = os.path.join(BASE_DIR, "hr-dashboard-project", "dataset.csv")
    df = pd.read_csv(
        path,
        sep=";",
        parse_dates=["Birthdate", "Hiredate"],
        dayfirst=True,
    )
    # Termdate may have blanks — parse separately to handle NaT
    df["Termdate"] = pd.to_datetime(df["Termdate"], dayfirst=True, errors="coerce")
    return df


@pytest.fixture(scope="session")
def vuln_df() -> pd.DataFrame:
    """Load CISO Cybersecurity vulnerabilities with comma delimiter and date parsing."""
    path = os.path.join(
        BASE_DIR, "ciso-cybersecurity-project", "vulnerabilities.csv"
    )
    df = pd.read_csv(
        path,
        sep=",",
        parse_dates=["First_Seen", "Last_Seen"],
    )
    # Remediated_Date may be blank for open vulns
    df["Remediated_Date"] = pd.to_datetime(
        df["Remediated_Date"], errors="coerce"
    )
    return df


@pytest.fixture(scope="session")
def jira_df() -> pd.DataFrame:
    """Load IT Project Management JIRA issues with comma delimiter and date parsing."""
    path = os.path.join(
        BASE_DIR, "it-project-mgmt-project", "jira_issues.csv"
    )
    df = pd.read_csv(
        path,
        sep=",",
        parse_dates=["Created_Date", "Updated_Date", "Sprint_Start", "Sprint_End"],
    )
    # Resolved_Date may be blank for open issues
    df["Resolved_Date"] = pd.to_datetime(
        df["Resolved_Date"], errors="coerce"
    )
    return df
