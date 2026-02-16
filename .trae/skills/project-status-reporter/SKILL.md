---
name: "project-status-reporter"
description: "Generates a project status report and dashboard. Invoke when user asks for project overview, progress update, or governance status."
---

# Project Status Reporter

This skill generates a comprehensive project status report, including current state, next steps, and workline breakdowns, and saves it as a static HTML dashboard.

## When to Use

- User asks for "project status", "progress report", "governance overview", or "what's next".
- User wants to visualize the current state of the 8 core worklines.
- User needs a quick snapshot of the project for stakeholders.

## Steps

1.  **Analyze Project State**:
    -   Review `AGENTS.md`, `coordination/dispatch/`, and `docs/` for latest context.
    -   Check `logs/daily/` for recent activities.
    -   Query Linear (via script or API if available) for task status.
    -   Check `migrations/` for database schema status.

2.  **Generate Report Content**:
    -   **Executive Summary**: High-level project phase and key blockers.
    -   **8 Worklines Status**: Breakdown of each workline (Engineering Supervisor, Core Engine, etc.) with:
        -   Current Status (Green/Yellow/Red)
        -   Recent Achievements
        -   Next Actions (P0/P1)
    -   **Architecture & Tech Stack**: Key decisions (e.g., PG-Only, Schema Isolation).
    -   **Metrics**: Auto-pass rate, coverage (if available).

3.  **Create Static Dashboard**:
    -   Generate a single-file HTML (`output/dashboard/project_status.html`).
    -   Use a modern, clean CSS framework (e.g., Tailwind via CDN or simple internal CSS).
    -   Include:
        -   Timestamp of generation.
        -   Color-coded status indicators.
        -   Collapsible sections for details.
    -   **Do not** require a backend server; file should open directly in browser.

4.  **Update Documentation**:
    -   Update `docs/project_status.md` (or similar) with the markdown version of the report.

5.  **Notify User**:
    -   Provide the path to the generated HTML file.
    -   Summarize the top 3 risks or next steps in the chat.

## Template (HTML Structure)

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Status Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 p-8">
    <div class="max-w-4xl mx-auto bg-white shadow-lg rounded-lg p-6">
        <h1 class="text-3xl font-bold mb-4">🚀 Spatial Intelligence Data Factory - Status Report</h1>
        <p class="text-gray-500 mb-8">Generated at: <span id="timestamp"></span></p>

        <!-- Executive Summary -->
        <section class="mb-8">
            <h2 class="text-xl font-semibold border-b pb-2 mb-4">📊 Executive Summary</h2>
            <div id="summary-content" class="prose">
                <!-- Content goes here -->
            </div>
        </section>

        <!-- Worklines Grid -->
        <section>
            <h2 class="text-xl font-semibold border-b pb-2 mb-4">🛠️ 8 Core Worklines</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4" id="worklines-grid">
                <!-- Workline Cards go here -->
            </div>
        </section>
    </div>
    <script>
        document.getElementById('timestamp').textContent = new Date().toLocaleString();
    </script>
</body>
</html>
```
