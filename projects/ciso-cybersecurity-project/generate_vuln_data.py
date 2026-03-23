#!/usr/bin/env python3
"""
Generate mock Tenable-style vulnerability dataset for CISO Cybersecurity dashboard demo.

Produces ~200 rows with realistic distributions:
- Severity: ~5% Critical, ~15% High, ~40% Medium, ~40% Low
- Remediation: ~60% Remediated, ~30% Open, ~10% Accepted
- CVSS scores correlated with severity levels
- Realistic hostnames, IPs, business units, and OS distributions

Usage:
    python generate_vuln_data.py
"""

import csv
import random
import os
from datetime import datetime, timedelta

# Seed for reproducibility
random.seed(42)

# --- Configuration ---
NUM_ROWS = 200
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vulnerabilities.csv")

# Severity distribution weights
SEVERITY_WEIGHTS = {
    "Critical": 0.05,
    "High": 0.15,
    "Medium": 0.40,
    "Low": 0.40,
}

# Remediation status distribution
REMEDIATION_WEIGHTS = {
    "Remediated": 0.60,
    "Open": 0.30,
    "Accepted": 0.10,
}

# CVSS score ranges by severity
CVSS_RANGES = {
    "Critical": (9.0, 10.0),
    "High": (7.0, 8.9),
    "Medium": (4.0, 6.9),
    "Low": (0.1, 3.9),
}

# Business units
BUSINESS_UNITS = [
    "Enterprise IT",
    "Finance & Accounting",
    "Human Resources",
    "Manufacturing Operations",
    "Research & Development",
    "Supply Chain",
    "Legal & Compliance",
    "Executive Office",
]

# Operating systems
OPERATING_SYSTEMS = [
    "Windows Server 2019",
    "Windows Server 2022",
    "Windows 10 Enterprise",
    "Windows 11 Enterprise",
    "Red Hat Enterprise Linux 8",
    "Red Hat Enterprise Linux 9",
    "Ubuntu 22.04 LTS",
    "CentOS 7",
    "VMware ESXi 7.0",
    "Cisco IOS 15.7",
]

# Hostname prefixes by business unit
HOSTNAME_PREFIXES = {
    "Enterprise IT": ["SRV-IT", "DC-CORE", "WEB-DMZ", "APP-INT"],
    "Finance & Accounting": ["SRV-FIN", "DB-FIN", "APP-FIN"],
    "Human Resources": ["SRV-HR", "APP-HR"],
    "Manufacturing Operations": ["SRV-MFG", "PLC-MFG", "HMI-MFG", "SCADA"],
    "Research & Development": ["SRV-RND", "LAB-RND", "DEV-RND"],
    "Supply Chain": ["SRV-SCM", "WMS-SCM", "APP-SCM"],
    "Legal & Compliance": ["SRV-LEG", "APP-LEG"],
    "Executive Office": ["SRV-EXEC", "WKS-EXEC"],
}

# Realistic Tenable plugin names and IDs
PLUGINS = [
    (19506, "Nessus Scan Information"),
    (10863, "SSL Certificate Information"),
    (42873, "SSL Medium Strength Cipher Suites Supported"),
    (57582, "SSL Self-Signed Certificate"),
    (65821, "SSL RC4 Cipher Suites Supported"),
    (104743, "TLS Version 1.0 Protocol Detection"),
    (157288, "TLS Version 1.1 Protocol Deprecated"),
    (11219, "Nessus SYN Scanner"),
    (34477, "SSL Certificate Expiry"),
    (35291, "SSL Certificate Signed Using Weak Hashing Algorithm"),
    (20007, "SSL Version 2 and 3 Protocol Detection"),
    (22964, "Service Detection"),
    (56984, "SSL / TLS Versions Supported"),
    (10287, "Traceroute Information"),
    (45590, "Common Platform Enumeration (CPE)"),
    (97833, "Microsoft Windows SMB Multiple Vulnerabilities"),
    (100871, "Microsoft Windows SMBv1 Multiple Vulnerabilities"),
    (110385, "Apache HTTP Server Multiple Vulnerabilities"),
    (125835, "OpenSSL Multiple Vulnerabilities"),
    (132456, "Oracle Java SE Multiple Vulnerabilities"),
    (140290, "Microsoft Exchange Server Remote Code Execution"),
    (148231, "Apache Log4j Remote Code Execution (Log4Shell)"),
    (153642, "Spring Framework Remote Code Execution (Spring4Shell)"),
    (156789, "Microsoft Windows Print Spooler Elevation of Privilege (PrintNightmare)"),
    (159123, "VMware vCenter Server Remote Code Execution"),
    (161456, "Cisco IOS XE Web UI Command Injection"),
    (163789, "Fortinet FortiOS SSL-VPN Remote Code Execution"),
    (166012, "Citrix ADC and Gateway Remote Code Execution"),
    (168345, "MOVEit Transfer SQL Injection"),
    (170678, "Barracuda ESG Remote Command Injection"),
    (172901, "Ivanti Connect Secure Authentication Bypass"),
    (175234, "Confluence Server Remote Code Execution"),
    (177567, "Zimbra Collaboration Suite Command Injection"),
    (179890, "Progress WS_FTP Server Deserialization Vulnerability"),
    (182123, "Atlassian Confluence Data Center Template Injection"),
    (184456, "JetBrains TeamCity Authentication Bypass"),
    (186789, "SolarWinds Access Rights Manager Remote Code Execution"),
    (189012, "Juniper Networks Junos OS Remote Code Execution"),
    (191345, "F5 BIG-IP Configuration Utility Authentication Bypass"),
    (193678, "Microsoft Outlook Elevation of Privilege (NTLM Relay)"),
]

# CVE ID ranges by year
CVE_YEARS = [2022, 2023, 2024, 2025, 2026]
CVE_YEAR_WEIGHTS = [0.10, 0.15, 0.30, 0.30, 0.15]

# Date range for first_seen / last_seen
DATE_START = datetime(2024, 1, 1)
DATE_END = datetime(2026, 3, 15)


def generate_cve_id():
    """Generate a realistic CVE ID."""
    year = random.choices(CVE_YEARS, weights=CVE_YEAR_WEIGHTS, k=1)[0]
    seq = random.randint(1000, 49999)
    return f"CVE-{year}-{seq}"


def generate_ip(bu_index):
    """Generate a realistic private IP address based on business unit."""
    subnet = 10 + bu_index
    return f"10.{subnet}.{random.randint(1, 254)}.{random.randint(1, 254)}"


def generate_hostname(business_unit, index):
    """Generate a realistic hostname."""
    prefixes = HOSTNAME_PREFIXES[business_unit]
    prefix = random.choice(prefixes)
    return f"{prefix}-{index:03d}"


def random_date(start, end):
    """Generate a random date between start and end."""
    delta = end - start
    random_days = random.randint(0, delta.days)
    return start + timedelta(days=random_days)


def generate_vulnerabilities():
    """Generate the full vulnerability dataset."""
    severities = list(SEVERITY_WEIGHTS.keys())
    severity_weights = list(SEVERITY_WEIGHTS.values())

    remediation_statuses = list(REMEDIATION_WEIGHTS.keys())
    remediation_weights = list(REMEDIATION_WEIGHTS.values())

    rows = []
    hostname_counter = {}

    for _ in range(NUM_ROWS):
        # Severity
        severity = random.choices(severities, weights=severity_weights, k=1)[0]

        # Business unit
        business_unit = random.choice(BUSINESS_UNITS)

        # Hostname
        if business_unit not in hostname_counter:
            hostname_counter[business_unit] = 0
        hostname_counter[business_unit] += 1
        hostname = generate_hostname(business_unit, hostname_counter[business_unit])

        # Plugin
        plugin_id, plugin_name = random.choice(PLUGINS)

        # CVE
        cve_id = generate_cve_id()

        # Dates
        first_seen = random_date(DATE_START, DATE_END - timedelta(days=30))
        last_seen = random_date(first_seen, min(first_seen + timedelta(days=180), DATE_END))

        # Remediation status
        remediation_status = random.choices(
            remediation_statuses, weights=remediation_weights, k=1
        )[0]

        # Remediated date
        if remediation_status == "Remediated":
            min_remediation = first_seen + timedelta(days=1)
            max_remediation = min(last_seen + timedelta(days=30), DATE_END)
            remediated_date = random_date(min_remediation, max_remediation).strftime(
                "%Y-%m-%d"
            )
        else:
            remediated_date = ""

        # CVSS score
        cvss_low, cvss_high = CVSS_RANGES[severity]
        cvss_score = round(random.uniform(cvss_low, cvss_high), 1)

        # OS
        asset_os = random.choice(OPERATING_SYSTEMS)

        # IP
        bu_index = BUSINESS_UNITS.index(business_unit)
        asset_ip = generate_ip(bu_index)

        rows.append(
            {
                "CVE_ID": cve_id,
                "Severity": severity,
                "Asset_Hostname": hostname,
                "Plugin_ID": plugin_id,
                "Plugin_Name": plugin_name,
                "First_Seen": first_seen.strftime("%Y-%m-%d"),
                "Last_Seen": last_seen.strftime("%Y-%m-%d"),
                "Remediated_Date": remediated_date,
                "Remediation_Status": remediation_status,
                "CVSS_Score": cvss_score,
                "Asset_OS": asset_os,
                "Asset_IP": asset_ip,
                "Business_Unit": business_unit,
            }
        )

    return rows


def main():
    """Generate vulnerability data and write to CSV."""
    rows = generate_vulnerabilities()

    fieldnames = [
        "CVE_ID",
        "Severity",
        "Asset_Hostname",
        "Plugin_ID",
        "Plugin_Name",
        "First_Seen",
        "Last_Seen",
        "Remediated_Date",
        "Remediation_Status",
        "CVSS_Score",
        "Asset_OS",
        "Asset_IP",
        "Business_Unit",
    ]

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Print summary statistics
    severity_counts = {}
    status_counts = {}
    for row in rows:
        severity_counts[row["Severity"]] = severity_counts.get(row["Severity"], 0) + 1
        status_counts[row["Remediation_Status"]] = (
            status_counts.get(row["Remediation_Status"], 0) + 1
        )

    print(f"Generated {len(rows)} vulnerability records to {OUTPUT_FILE}")
    print("\nSeverity Distribution:")
    for sev in ["Critical", "High", "Medium", "Low"]:
        count = severity_counts.get(sev, 0)
        pct = count / len(rows) * 100
        print(f"  {sev}: {count} ({pct:.1f}%)")

    print("\nRemediation Status:")
    for status in ["Open", "Remediated", "Accepted"]:
        count = status_counts.get(status, 0)
        pct = count / len(rows) * 100
        print(f"  {status}: {count} ({pct:.1f}%)")


if __name__ == "__main__":
    main()
