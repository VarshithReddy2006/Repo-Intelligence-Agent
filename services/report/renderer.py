"""Report Rendering Engine.

Handles formatting and compilation of the ReportDataModel into HTML,
Markdown, and PDF files.
"""

from typing import Dict, Any, Optional
import os
from jinja2 import Template

from models.report import ReportDataModel


class HTMLRenderer:
    """Compiles the ReportDataModel into a self-contained interactive HTML page."""

    TEMPLATE_STR = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Repository Intelligence Report - {{ report.metadata.repo_name }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0b0f19;
            --bg-secondary: #161f30;
            --bg-tertiary: #1f2c45;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-primary: #3b82f6;
            --accent-secondary: #6366f1;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --border-color: #2e3f5b;
            --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
            --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
            --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
        }

        [data-theme="light"] {
            --bg-primary: #f8fafc;
            --bg-secondary: #ffffff;
            --bg-tertiary: #f1f5f9;
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --accent-primary: #2563eb;
            --accent-secondary: #4f46e5;
            --success: #059669;
            --warning: #d97706;
            --danger: #dc2626;
            --border-color: #e2e8f0;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.5;
            padding: 2rem;
            transition: background-color 0.3s, color 0.3s;
        }

        /* Container Layout */
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2.5rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--border-color);
        }

        .header-title h1 {
            font-size: 2.25rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.25rem;
        }

        .header-title p {
            color: var(--text-secondary);
            font-size: 1rem;
        }

        .header-actions {
            display: flex;
            gap: 1rem;
            align-items: center;
        }

        .btn {
            background-color: var(--accent-primary);
            color: white;
            border: none;
            padding: 0.625rem 1.25rem;
            border-radius: 0.5rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .btn:hover {
            opacity: 0.9;
            transform: translateY(-1px);
        }

        .btn-secondary {
            background-color: var(--bg-secondary);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
        }

        /* Theme Toggle */
        .theme-toggle {
            background: none;
            border: none;
            cursor: pointer;
            padding: 0.5rem;
            color: var(--text-primary);
            border-radius: 0.375rem;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1px solid var(--border-color);
            background-color: var(--bg-secondary);
        }

        /* Tab Navigation */
        .tabs {
            display: flex;
            gap: 0.5rem;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 2rem;
            padding-bottom: 0.5rem;
            overflow-x: auto;
        }

        .tab-btn {
            padding: 0.75rem 1.5rem;
            border: none;
            background: none;
            color: var(--text-secondary);
            font-weight: 500;
            font-size: 1rem;
            cursor: pointer;
            border-radius: 0.5rem;
            transition: all 0.2s;
            white-space: nowrap;
        }

        .tab-btn:hover {
            color: var(--text-primary);
            background-color: var(--bg-tertiary);
        }

        .tab-btn.active {
            color: white;
            background-color: var(--accent-primary);
        }

        /* Tab Content */
        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        /* Grid Layouts */
        .grid-3 {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .grid-2 {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(480px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        /* Card Component */
        .card {
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 0.75rem;
            padding: 1.5rem;
            box-shadow: var(--shadow-md);
            margin-bottom: 1.5rem;
        }

        .card-header {
            font-size: 1.15rem;
            font-weight: 600;
            margin-bottom: 1.25rem;
            color: var(--text-primary);
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 0.75rem;
        }

        /* Overall Score Layout */
        .score-circle-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 1rem 0;
        }

        .score-circle {
            width: 150px;
            height: 150px;
            border-radius: 50%;
            border: 10px solid var(--border-color);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            position: relative;
            margin-bottom: 1rem;
        }

        .score-circle.grade-A { border-color: var(--success); }
        .score-circle.grade-B { border-color: var(--accent-primary); }
        .score-circle.grade-C { border-color: var(--warning); }
        .score-circle.grade-D { border-color: var(--danger); }
        .score-circle.grade-F { border-color: var(--danger); }

        .score-value {
            font-size: 2.5rem;
            font-weight: 700;
        }

        .score-grade {
            font-size: 1.15rem;
            font-weight: 600;
            color: var(--text-secondary);
        }

        /* Progress Bar */
        .metric-row {
            margin-bottom: 1.25rem;
        }

        .metric-header {
            display: flex;
            justify-content: space-between;
            font-size: 0.9rem;
            margin-bottom: 0.375rem;
            color: var(--text-secondary);
        }

        .progress-bar-bg {
            background-color: var(--bg-tertiary);
            height: 8px;
            border-radius: 4px;
            overflow: hidden;
        }

        .progress-bar-fill {
            background-color: var(--accent-primary);
            height: 100%;
            border-radius: 4px;
        }

        .progress-bar-fill.success { background-color: var(--success); }
        .progress-bar-fill.warning { background-color: var(--warning); }
        .progress-bar-fill.danger { background-color: var(--danger); }

        /* General styled list */
        .styled-list {
            list-style: none;
        }

        .styled-list li {
            padding: 0.75rem 0;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-secondary);
            font-size: 0.95rem;
        }

        .styled-list li:last-child {
            border-bottom: none;
        }

        .styled-list .item-title {
            color: var(--text-primary);
            font-weight: 500;
        }

        /* Priority list items (badges) */
        .priority-item {
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            padding: 0.75rem 0;
            border-bottom: 1px solid var(--border-color);
        }

        .priority-item:last-child {
            border-bottom: none;
        }

        .priority-badge {
            background-color: var(--danger);
            color: white;
            font-size: 0.75rem;
            padding: 0.15rem 0.5rem;
            border-radius: 0.25rem;
            font-weight: 600;
        }

        .priority-badge.warning {
            background-color: var(--warning);
        }

        /* Code display blocks */
        code {
            font-family: monospace;
            background-color: var(--bg-tertiary);
            padding: 0.2rem 0.4rem;
            border-radius: 0.25rem;
            font-size: 0.9rem;
        }

        pre {
            background-color: var(--bg-tertiary);
            padding: 1rem;
            border-radius: 0.5rem;
            overflow-x: auto;
            border: 1px solid var(--border-color);
            margin: 1rem 0;
        }

        /* Table */
        .table-container {
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.95rem;
            text-align: left;
        }

        th {
            background-color: var(--bg-tertiary);
            padding: 0.75rem 1rem;
            font-weight: 600;
            color: var(--text-primary);
            border-bottom: 2px solid var(--border-color);
        }

        td {
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-secondary);
        }

        tr:last-child td {
            border-bottom: none;
        }

        /* Print formatting */
        @media print {
            body {
                background: white !important;
                color: black !important;
                padding: 0 !important;
            }
            .card {
                box-shadow: none !important;
                border: 1px solid #ccc !important;
                page-break-inside: avoid;
            }
            .tabs, .theme-toggle, .btn {
                display: none !important;
            }
            .tab-content {
                display: block !important;
                margin-bottom: 2rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-title">
                <h1>Repository Intelligence Report</h1>
                <p>{{ report.metadata.repo_name }} &bull; Generated at {{ report.metadata.generated_at }}</p>
            </div>
            <div class="header-actions">
                <button class="theme-toggle" id="themeToggleBtn" onclick="toggleTheme()" title="Toggle Light/Dark Theme">
                    🌓
                </button>
                <button class="btn btn-secondary" onclick="window.print()">Export / Print</button>
            </div>
        </header>

        <!-- Tabs Menu -->
        <nav class="tabs">
            <button class="tab-btn active" onclick="switchTab(event, 'overview')">Overview</button>
            <button class="tab-btn" onclick="switchTab(event, 'architecture')">Architecture & Coupling</button>
            <button class="tab-btn" onclick="switchTab(event, 'api')">API & Stability</button>
            <button class="tab-btn" onclick="switchTab(event, 'hygiene')">Code Hygiene</button>
            <button class="tab-btn" onclick="switchTab(event, 'walkthrough')">Onboarding Guide</button>
        </nav>

        <!-- OVERVIEW TAB -->
        <div id="overview" class="tab-content active">
            <div class="grid-3">
                <!-- Score Card -->
                <div class="card score-circle-container">
                    <div class="score-circle grade-{{ report.scores.grade }}">
                        <span class="score-value">{{ report.scores.overall }}</span>
                        <span class="score-grade">Score</span>
                    </div>
                    <h3>Grade: {{ report.scores.grade }}</h3>
                </div>

                <!-- Scores Breakdown -->
                <div class="card">
                    <div class="card-header">Health Components</div>
                    <div class="metric-row">
                        <div class="metric-header">
                            <span>Architecture Stability</span>
                            <span>{{ report.scores.architecture }}/100</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill {% if report.scores.architecture >= 80 %}success{% elif report.scores.architecture >= 60 %}warning{% else %}danger{% endif %}" style="width: {{ report.scores.architecture }}%"></div>
                        </div>
                    </div>
                    <div class="metric-row">
                        <div class="metric-header">
                            <span>API Quality & Distance</span>
                            <span>{{ report.scores.api }}/100</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill {% if report.scores.api >= 80 %}success{% elif report.scores.api >= 60 %}warning{% else %}danger{% endif %}" style="width: {{ report.scores.api }}%"></div>
                        </div>
                    </div>
                    <div class="metric-row">
                        <div class="metric-header">
                            <span>Code Hygiene</span>
                            <span>{{ report.scores.hygiene }}/100</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill {% if report.scores.hygiene >= 80 %}success{% elif report.scores.hygiene >= 60 %}warning{% else %}danger{% endif %}" style="width: {{ report.scores.hygiene }}%"></div>
                        </div>
                    </div>
                    <div class="metric-row">
                        <div class="metric-header">
                            <span>Hotspot & Churn Risk</span>
                            <span>{{ report.scores.churn }}/100</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill {% if report.scores.churn >= 80 %}success{% elif report.scores.churn >= 60 %}warning{% else %}danger{% endif %}" style="width: {{ report.scores.churn }}%"></div>
                        </div>
                    </div>
                    <div class="metric-row">
                        <div class="metric-header">
                            <span>Onboarding Clarity</span>
                            <span>{{ report.scores.readability }}/100</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill {% if report.scores.readability >= 80 %}success{% elif report.scores.readability >= 60 %}warning{% else %}danger{% endif %}" style="width: {{ report.scores.readability }}%"></div>
                        </div>
                    </div>
                </div>

                <!-- Stats Panel -->
                <div class="card">
                    <div class="card-header">Repository Metadata</div>
                    <ul class="styled-list">
                        <li><span class="item-title">Lines of Code:</span> {{ report.metadata.total_loc }}</li>
                        <li><span class="item-title">Commit Count:</span> {{ report.metadata.commits_count }}</li>
                        <li><span class="item-title">Report Time:</span> {{ report.metadata.execution_time_ms }} ms</li>
                        <li>
                            <span class="item-title">Languages:</span>
                            {% for lang, pct in report.metadata.languages.items() %}
                                {{ lang }} ({{ pct }}%){% if not loop.last %}, {% endif %}
                            {% endfor %}
                        </li>
                    </ul>
                </div>
            </div>

            <!-- Prioritized Action Recommendations -->
            <div class="card">
                <div class="card-header">Prioritized Action Items & Refactoring Priorities</div>
                {% for prio in report.refactoring_priorities %}
                    <div class="priority-item">
                        <span class="priority-badge {% if 'volatile' in prio.lower() %}danger{% else %}warning{% endif %}">
                            {% if 'volatile' in prio.lower() %}HIGH RISK{% else %}CLEANUP{% endif %}
                        </span>
                        <span>{{ prio }}</span>
                    </div>
                {% endfor %}
            </div>
        </div>

        <!-- ARCHITECTURE TAB -->
        <div id="architecture" class="tab-content">
            <div class="grid-2">
                <div class="card">
                    <div class="card-header">Structure Metrics</div>
                    <ul class="styled-list">
                        <li><span class="item-title">Circular Dependencies Count:</span> {{ report.architecture.cycles_count }}</li>
                        <li><span class="item-title">Strongly Connected Clusters:</span> {{ report.architecture.strongly_connected_components }}</li>
                        <li><span class="item-title">Design Smells Count:</span> {{ report.architecture.smells_count }}</li>
                    </ul>
                </div>

                <div class="card">
                    <div class="card-header">Dependency Design Violations</div>
                    {% if report.architecture.smells %}
                        <ul class="styled-list">
                            {% for smell in report.architecture.smells %}
                                <li>{{ smell }}</li>
                            {% endfor %}
                        </ul>
                    {% else %}
                        <p style="color: var(--text-secondary);">No dependency smells detected in the architecture graph.</p>
                    {% endif %}
                </div>
            </div>

            <div class="card">
                <div class="card-header">Circular Import Paths</div>
                {% if report.architecture.cycles %}
                    <ul class="styled-list">
                        {% for cycle in report.architecture.cycles %}
                            <li>
                                <code>{{ cycle | join(' &rarr; ') }} &rarr; {{ cycle[0] }}</code>
                            </li>
                        {% endfor %}
                    </ul>
                {% else %}
                    <p style="color: var(--text-secondary);">No circular import cycles detected.</p>
                {% endif %}
            </div>
        </div>

        <!-- API TAB -->
        <div id="api" class="tab-content">
            <div class="card">
                <div class="card-header">API Stability & Packaging Metrics</div>
                <div class="grid-3" style="margin-top: 1rem;">
                    <div>
                        <h4 style="color: var(--text-secondary); margin-bottom: 0.25rem;">Total Exported Symbols</h4>
                        <span style="font-size: 1.75rem; font-weight: 700;">{{ report.api_surface.total_exported_symbols }}</span>
                    </div>
                    <div>
                        <h4 style="color: var(--text-secondary); margin-bottom: 0.25rem;">Public / Private Ratio</h4>
                        <span style="font-size: 1.75rem; font-weight: 700;">{{ report.api_surface.public_private_ratio }}</span>
                    </div>
                    <div>
                        <h4 style="color: var(--text-secondary); margin-bottom: 0.25rem;">Distance Main Sequence</h4>
                        <span style="font-size: 1.75rem; font-weight: 700;">{{ report.api_surface.average_distance_main_sequence }}</span>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">API Surface Guidelines</div>
                <p style="color: var(--text-secondary); margin-bottom: 1rem;">
                    An balanced API surface has a reasonable public-to-private ratio (typically 0.1 to 0.4), signifying that internal helpers are encapsulated and only core interfaces are exposed. High instability distance flags packages violating stable dependency patterns.
                </p>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Category</th>
                                <th>Value</th>
                                <th>Reference Thresholds</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Average Distance</td>
                                <td><code>{{ report.api_surface.average_distance_main_sequence }}</code></td>
                                <td>Balanced: &le; 0.3 | Imbalanced: &gt; 0.3</td>
                            </tr>
                            <tr>
                                <td>Public / Private Ratio</td>
                                <td><code>{{ report.api_surface.public_private_ratio }}</code></td>
                                <td>Good: 0.1 - 0.5 | Fragile: &gt; 0.5</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- HYGIENE TAB -->
        <div id="hygiene" class="tab-content">
            <div class="grid-2">
                <div class="card">
                    <div class="card-header">Cleanliness Metrics</div>
                    <ul class="styled-list">
                        <li><span class="item-title">Unused / Dead Functions:</span> {{ report.hygiene.dead_functions_count }}</li>
                        <li><span class="item-title">Dead Code Ratio:</span> {{ report.hygiene.dead_code_ratio }}%</li>
                    </ul>
                </div>

                <div class="card">
                    <div class="card-header">Refactoring Recommendations</div>
                    <p style="color: var(--text-secondary);">
                        Removing dead functions reduces code footprint, increases compilation speed, and prevents developer confusion. Prioritize deleting symbols with 0 call-graph references.
                    </p>
                </div>
            </div>

            <div class="card">
                <div class="card-header">Dead Code Registry</div>
                {% if report.hygiene.dead_functions %}
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Unused Module / Function Path</th>
                                    <th>Clean Recommendation</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for dead in report.hygiene.dead_functions %}
                                    <tr>
                                        <td><code>{{ dead }}</code></td>
                                        <td>This module has 0 active references. Confirm removal.</td>
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                {% else %}
                    <p style="color: var(--text-secondary);">No dead functions detected in the symbol sweep.</p>
                {% endif %}
            </div>
        </div>

        <!-- WALKTHROUGH TAB -->
        <div id="walkthrough" class="tab-content">
            <div class="grid-2">
                <div class="card">
                    <div class="card-header">Onboarding Checklist</div>
                    <ul class="styled-list">
                        <li><span class="item-title">Walkthrough Coverage:</span> {{ report.onboarding.reading_path_completeness }}%</li>
                        <li><span class="item-title">Main Entry Points:</span> {{ report.onboarding.core_entry_points | length }}</li>
                    </ul>
                </div>

                <div class="card">
                    <div class="card-header">Main Entry Points</div>
                    {% if report.onboarding.core_entry_points %}
                        <ul class="styled-list">
                            {% for entry in report.onboarding.core_entry_points %}
                                <li><code>{{ entry }}</code></li>
                            {% endfor %}
                        </ul>
                    {% else %}
                        <p style="color: var(--text-secondary);">No primary entry points detected dynamically.</p>
                    {% endif %}
                </div>
            </div>

            <div class="card">
                <div class="card-header">Recommended Reading Order Guide</div>
                <p style="color: var(--text-secondary); margin-bottom: 1rem;">
                    For developers onboarding to this project, read the files in the following topological order to understand dependencies sequentially:
                </p>
                {% if report.onboarding.recommended_reading_path %}
                    <ol class="styled-list" style="list-style: decimal; padding-left: 1.5rem;">
                        {% for step in report.onboarding.recommended_reading_path %}
                            <li style="padding: 0.5rem 0;"><code>{{ step }}</code></li>
                        {% endfor %}
                    </ol>
                {% else %}
                    <p style="color: var(--text-secondary);">No reading path compiled for this repository context.</p>
                {% endif %}
            </div>
        </div>
    </div>

    <!-- Script for Tab switching and Theme selection -->
    <script>
        function switchTab(evt, tabId) {
            // Hide all tab contents
            const contents = document.querySelectorAll('.tab-content');
            contents.forEach(content => content.classList.remove('active'));

            // Remove active class from all tab buttons
            const buttons = document.querySelectorAll('.tab-btn');
            buttons.forEach(btn => btn.classList.remove('active'));

            // Show current tab, mark button as active
            document.getElementById(tabId).classList.add('active');
            evt.currentTarget.classList.add('active');
        }

        function toggleTheme() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            if (currentTheme === 'light') {
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
            } else {
                document.documentElement.setAttribute('data-theme', 'light');
                localStorage.setItem('theme', 'light');
            }
        }

        // Initialize theme from localStorage
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            document.documentElement.setAttribute('data-theme', savedTheme);
        } else {
            // Check system preference
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
        }
    </script>
</body>
</html>
"""

    def render(self, report: ReportDataModel) -> bytes:
        """Renders ReportDataModel to self-contained HTML bytes using Jinja2."""
        template = Template(self.TEMPLATE_STR)
        html_str = template.render(report=report)
        return html_str.encode("utf-8")


class MarkdownRenderer:
    """Compiles the ReportDataModel into a GitHub-flavored Markdown document."""

    TEMPLATE_STR = """# Repository Health Report: {{ report.metadata.repo_name }}
Generated at: {{ report.metadata.generated_at }} (Execution: {{ report.metadata.execution_time_ms }} ms)

## Health Summary
- **Overall Score**: {{ report.scores.overall }} / 100 (Grade: {{ report.scores.grade }})
- **Architecture Stability**: {{ report.scores.architecture }} / 100
- **API Quality & Distance**: {{ report.scores.api }} / 100
- **Code Hygiene**: {{ report.scores.hygiene }} / 100
- **Hotspot & Churn Risk**: {{ report.scores.churn }} / 100
- **Onboarding Clarity**: {{ report.scores.readability }} / 100

### Repository Stats
- **Lines of Code**: {{ report.metadata.total_loc }}
- **Commit Count**: {{ report.metadata.commits_count }}
- **Languages**: {% for lang, pct in report.metadata.languages.items() %}{{ lang }} ({{ pct }}%){% if not loop.last %}, {% endif %}{% endfor %}

---

## Refactoring Priorities
{% for prio in report.refactoring_priorities -%}
- **{% if 'volatile' in prio.lower() %}HIGH RISK{% else %}CLEANUP{% endif %}**: {{ prio }}
{% endfor %}

---

## Architecture & Coupling
- **Circular Dependencies Count**: {{ report.architecture.cycles_count }}
- **Strongly Connected Clusters**: {{ report.architecture.strongly_connected_components }}
- **Design Smells Count**: {{ report.architecture.smells_count }}

<details>
<summary><b>View Circular Import Paths</b></summary>

{% if report.architecture.cycles -%}
{% for cycle in report.architecture.cycles -%}
- `{{ cycle | join(' -> ') }} -> {{ cycle[0] }}`
{% endfor -%}
{%- else -%}
No circular import cycles detected.
{%- endif %}
</details>

<details>
<summary><b>View Design Smells Details</b></summary>

{% if report.architecture.smells -%}
{% for smell in report.architecture.smells -%}
- {{ smell }}
{% endfor -%}
{%- else -%}
No dependency smells detected.
{%- endif %}
</details>

---

## API & Stability
- **Total Exported Symbols**: {{ report.api_surface.total_exported_symbols }}
- **Public / Private Ratio**: {{ report.api_surface.public_private_ratio }}
- **Average Distance from Main Sequence**: {{ report.api_surface.average_distance_main_sequence }}

---

## Code Hygiene
- **Dead Functions Count**: {{ report.hygiene.dead_functions_count }}
- **Dead Code Ratio**: {{ report.hygiene.dead_code_ratio }}%

<details>
<summary><b>View Dead Code Registry</b></summary>

{% if report.hygiene.dead_functions -%}
{% for dead in report.hygiene.dead_functions -%}
- `{{ dead }}`
{% endfor -%}
{%- else -%}
No dead functions detected.
{%- endif %}
</details>

---

## Onboarding Walkthrough
- **Walkthrough Coverage**: {{ report.onboarding.reading_path_completeness }}%
- **Main Entry Points**: {% for entry in report.onboarding.core_entry_points -%}`{{ entry }}`{% if not loop.last %}, {% endif %}{% endfor %}

<details>
<summary><b>View Recommended Reading Order Guide</b></summary>

{% if report.onboarding.recommended_reading_path -%}
{% for step in report.onboarding.recommended_reading_path -%}
{{ loop.index }}. `{{ step }}`
{% endfor -%}
{%- else -%}
No reading path compiled.
{%- endif %}
</details>
"""

    def render(self, report: ReportDataModel) -> bytes:
        """Renders ReportDataModel to Markdown bytes using Jinja2."""
        template = Template(self.TEMPLATE_STR)
        markdown_str = template.render(report=report)
        return markdown_str.encode("utf-8")


class PDFRenderer:
    """PDF-friendly HTML Renderer.

    Generates the print-friendly HTML layout and appends an automatic print trigger script
    to launch browser printing/export on load.
    """

    def render(self, report: ReportDataModel) -> bytes:
        """Renders the HTML report with an automatic window.print() trigger."""
        html_bytes = HTMLRenderer().render(report)
        html_str = html_bytes.decode("utf-8")

        # Inject print trigger script right before </body>
        print_trigger = "\n<script>window.addEventListener('DOMContentLoaded', () => { window.print(); });</script>\n"
        if "</body>" in html_str:
            html_str = html_str.replace("</body>", f"{print_trigger}</body>")
        else:
            html_str += print_trigger

        return html_str.encode("utf-8")

