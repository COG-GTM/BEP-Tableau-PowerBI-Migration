# Dashboard Inventory

**Generated**: 2026-03-23T18:47:01.774282Z
**Source Document**: Public+Tableau+dashboards+and+Tableau+Exchange+resources.docx

---

## Summary

- **Total Dashboards to Convert**: 4
- **Total Calculated Fields**: 70
- **Complexity**: 3 High, 1 Medium, 0 Low

---

## Dashboards

### 1. Sales & Customer Dashboard

- **ID**: `sales-dashboard`
- **Complexity**: High
- **Calculated Fields**: 30
- **Pages**: Sales Dashboard, Customer Dashboard
- **Source Workbook**: `projects/sales-dashboard-project/Sales & Customer Dashboards.twbx`

**Datasets**:
  - `projects/sales-dashboard-project/datasets/non-eu/Orders.csv`
  - `projects/sales-dashboard-project/datasets/non-eu/Customers.csv`
  - `projects/sales-dashboard-project/datasets/non-eu/Products.csv`
  - `projects/sales-dashboard-project/datasets/non-eu/Location.csv`

**Key Conversion Challenges**:
  - LOD FIXED expressions
  - WINDOW_MAX/MIN
  - Parameters (What-If)
  - YoY comparisons
  - KPI indicators

**Output Files**:
  - dax_measures: `conversion-output/sales-dashboard/dax_measures.dax`
  - model: `conversion-output/sales-dashboard/model.tmdl`
  - layout: `conversion-output/sales-dashboard/layout.json`
  - theme: `conversion-output/sales-dashboard/theme.json`
  - power_query: `conversion-output/sales-dashboard/power_query.pq`
  - validation_report: `conversion-output/sales-dashboard/validation_report.md`

---

### 2. HR Dashboard

- **ID**: `hr-dashboard`
- **Complexity**: Medium
- **Calculated Fields**: 20
- **Pages**: HR Summary, HR Details
- **Source Workbook**: `projects/hr-dashboard-project/HR Dashboard.twbx`

**Datasets**:
  - `projects/hr-dashboard-project/dataset.csv`

**Key Conversion Challenges**:
  - DATEDIFF
  - CASE/WHEN
  - ISNULL
  - TOTAL()
  - RANK
  - WINDOW_MAX
  - Semicolon delimiters
  - EU date format (DD/MM/YYYY)

**Output Files**:
  - dax_measures: `conversion-output/hr-dashboard/dax_measures.dax`
  - model: `conversion-output/hr-dashboard/model.tmdl`
  - layout: `conversion-output/hr-dashboard/layout.json`
  - theme: `conversion-output/hr-dashboard/theme.json`
  - power_query: `conversion-output/hr-dashboard/power_query.pq`
  - validation_report: `conversion-output/hr-dashboard/validation_report.md`

---

### 3. CISO Cybersecurity Dashboard

- **ID**: `ciso-cybersecurity-dashboard`
- **Complexity**: High
- **Calculated Fields**: 10
- **Pages**: Executive Summary, Risk Heatmap
- **Source Workbook**: `N/A (mock dataset)`

**Datasets**:
  - `projects/ciso-cybersecurity-project/vulnerabilities.csv`

**Key Conversion Challenges**:
  - LOD FIXED (Risk Score by BU)
  - RUNNING_AVG (CVSS trend)
  - RANKX (Top 10 assets)
  - MTTR calculation
  - Tenable.io API connector

**Output Files**:
  - dax_measures: `conversion-output/ciso-cybersecurity-dashboard/dax_measures.dax`
  - model: `conversion-output/ciso-cybersecurity-dashboard/model.tmdl`
  - layout: `conversion-output/ciso-cybersecurity-dashboard/layout.json`
  - theme: `conversion-output/ciso-cybersecurity-dashboard/theme.json`
  - power_query: `conversion-output/ciso-cybersecurity-dashboard/power_query.pq`
  - validation_report: `conversion-output/ciso-cybersecurity-dashboard/validation_report.md`

---

### 4. IT Project Management Dashboard

- **ID**: `it-project-mgmt-dashboard`
- **Complexity**: High
- **Calculated Fields**: 10
- **Pages**: Sprint Overview, Team Workload
- **Source Workbook**: `N/A (mock dataset)`

**Datasets**:
  - `projects/it-project-mgmt-project/jira_issues.csv`

**Key Conversion Challenges**:
  - Burn-down chart (RUNNING_SUM reverse)
  - WINDOW_AVG (3-sprint moving avg)
  - Scope Creep detection
  - Sprint Velocity
  - JIRA REST API connector

**Output Files**:
  - dax_measures: `conversion-output/it-project-mgmt-dashboard/dax_measures.dax`
  - model: `conversion-output/it-project-mgmt-dashboard/model.tmdl`
  - layout: `conversion-output/it-project-mgmt-dashboard/layout.json`
  - theme: `conversion-output/it-project-mgmt-dashboard/theme.json`
  - power_query: `conversion-output/it-project-mgmt-dashboard/power_query.pq`
  - validation_report: `conversion-output/it-project-mgmt-dashboard/validation_report.md`

---

## Reference Dashboards from Source Document

### Cyber Security Analysis
- **Category**: Cybersecurity / CISO-style dashboards
- Cyber Security Analysis
- Public Tableau dashboard with cyber-incident analysis by industry. Useful as an executive cyber-posture analog.
- **URL**: https://public.tableau.com/app/profile/sinamandla.mabaso/viz/CyberSecurityAnalysis_16915038943080/Dashboard1

### CVE Vulnerability Checker
- **Category**: Cybersecurity / CISO-style dashboards
- CVE Vulnerability Checker
- Public Tableau dashboard oriented around CVE and vulnerability-triage style analysis. Closest public analog to vulnerability-management reporting.
- **URL**: https://public.tableau.com/app/profile/kpmg.forensics/viz/CVEVulnerabilityChecker/CVEVulnerabilityChecker

### Cyber/Security Interactive Dashboard
- **Category**: Cybersecurity / CISO-style dashboards
- Cyber/Security Interactive Dashboard
- Older public Tableau cyber dashboard. More useful as layout and storytelling inspiration than as a current operating model.
- **URL**: https://public.tableau.com/app/profile/econleadership/viz/CyberSecurityDashboard/CyberBETA

### Vulnerability Assessment Dashboard 2023
- **Category**: Cybersecurity / CISO-style dashboards
- Vulnerability Assessment Dashboard 2023
- Another public vulnerability-themed Tableau example. Availability may vary, but it is indexed publicly.
- **URL**: https://public.tableau.com/app/profile/family.legacy/viz/VulnerabilityAssessmentDashboard2023/VulnerabilityAssessment2023Dashboard

### Risk Register (Tableau Exchange accelerator)
- **Category**: Cybersecurity / CISO-style dashboards
- Risk Register (Tableau Exchange accelerator)
- Official Tableau accelerator for risk tracking, prioritization, mitigation, and exposure monitoring. Strong fit for adapting into a CISO posture dashboard.
- **URL**: https://exchange.tableau.com/products/594

### PMO Project Management Dashboard
- **Category**: IT project management / Jira-style dashboards
- PMO Project Management Dashboard
- Public Tableau dashboard with portfolio status, project progress, budget consumption, and project-manager workload views.
- **URL**: https://public.tableau.com/app/profile/ervin.vinzon/viz/PMOProjectManagementDashboard/PMOProjectManagementDashboard

### PMO - Project Management Dashboard #RWFD #Exchange
- **Category**: IT project management / Jira-style dashboards
- PMO - Project Management Dashboard #RWFD #Exchange
- Public PMO dashboard focused on executive summary views. Good reference for PMO layout patterns.
- **URL**: https://public.tableau.com/app/profile/ajay.varghese/viz/PMO-ProjectManagementDashboardRWFDExchange/MainDashboard

### Project Management Action Dashboard
- **Category**: IT project management / Jira-style dashboards
- Project Management Action Dashboard
- Public Tableau dashboard focused on operational PM actions and status tracking.
- **URL**: https://public.tableau.com/app/profile/b.winsey/viz/ProjectManagementActionDashboard/PMDashboard

### Project Management Dashboard
- **Category**: IT project management / Jira-style dashboards
- Project Management Dashboard
- Public Tableau project-management redesign example. Good for summary and status framing.
- **URL**: https://public.tableau.com/app/profile/gandes.goldestan/viz/Projectmanagementoffice/Overview

### PMO - Project Portfolio
- **Category**: IT project management / Jira-style dashboards
- PMO - Project Portfolio
- Public Tableau view aligned to project portfolio oversight, including priority, risk, budget, and progress.
- **URL**: https://public.tableau.com/views/ProjectManagement-PMODashboard/Home

### Project Portfolio (Tableau Exchange accelerator)
- **Category**: IT project management / Jira-style dashboards
- Project Portfolio (Tableau Exchange accelerator)
- Official Tableau accelerator for project portfolio evaluation, budget consumption, progress tracking, and project risk identification.
- **URL**: https://exchange.tableau.com/products/582

### Jira (Tableau Exchange connector)
- **Category**: Connectors and Tableau official resources
- Jira (Tableau Exchange connector)
- Official Tableau Exchange connector for Jira. Relevant for pulling issues, stories, tasks, and related project data into Tableau.
- **URL**: https://exchange.tableau.com/products/1089

### Tableau Accelerators overview
- **Category**: Connectors and Tableau official resources
- Tableau Accelerators overview
- Official Tableau page for accelerators. Useful starting point for finding adjacent templates.
- **URL**: https://www.tableau.com/solutions/exchange/accelerators

### Tableau Exchange connectors
- **Category**: Connectors and Tableau official resources
- Tableau Exchange connectors
- Official Tableau Exchange connectors directory. Useful for identifying supported integration paths beyond Jira.
- **URL**: https://exchange.tableau.com/connectors

### REST API Connector (Tableau Exchange)
- **Category**: Connectors and Tableau official resources
- REST API Connector (Tableau Exchange)
- Official Tableau Exchange connector for REST APIs. Potential fallback if a target system is not covered by a native connector.
- **URL**: https://exchange.tableau.com/products/1111

### Closest CISO / vulnerability posture analog: CVE Vulnerability Checker
- **Category**: Best-fit shortlist
- Closest CISO / vulnerability posture analog: CVE Vulnerability Checker
- **URL**: https://public.tableau.com/app/profile/kpmg.forensics/viz/CVEVulnerabilityChecker/CVEVulnerabilityChecker

### Best official CISO-ish starting point: Risk Register
- **Category**: Best-fit shortlist
- Best official CISO-ish starting point: Risk Register
- **URL**: https://exchange.tableau.com/products/594

### Closest PM / executive portfolio analog: PMO Project Management Dashboard
- **Category**: Best-fit shortlist
- Closest PM / executive portfolio analog: PMO Project Management Dashboard
- **URL**: https://public.tableau.com/app/profile/ervin.vinzon/viz/PMOProjectManagementDashboard/PMOProjectManagementDashboard

### Best official PM / Jira starting point: Project Portfolio + Jira connector
- **Category**: Best-fit shortlist
- Best official PM / Jira starting point: Project Portfolio + Jira connector
- **URL**: https://exchange.tableau.com/products/582
- **URL**: https://exchange.tableau.com/products/1089

### Public dashboards that clearly expose live Tenable or live Jira backends are rare in Tableau Public
- **Category**: Notes
- Public dashboards that clearly expose live Tenable or live Jira backends are rare in Tableau Public. Most public examples are demos, redesigns, or dashboards built on public or synthetic data.

### The strongest practical pattern is usually: start from an official Tableau accelerator, then wire it to enterprise data through a connector such as Jira or a REST/API path
- **Category**: Notes
- The strongest practical pattern is usually: start from an official Tableau accelerator, then wire it to enterprise data through a connector such as Jira or a REST/API path.
