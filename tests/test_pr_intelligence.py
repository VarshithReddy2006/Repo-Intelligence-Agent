import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api import app
from models.pr_intelligence import PRAnalyzeRequest, ChangedFile, SymbolChange
from models.symbol import Symbol
from services.pr_intelligence_service import PRIntelligenceService
import networkx as nx

client = TestClient(app)


class TestPRIntelligence(unittest.TestCase):

    def setUp(self):
        self.service = PRIntelligenceService()

    def test_pr_url_parsing_valid(self):
        """Verifies that valid PR URLs are parsed correctly."""
        req = PRAnalyzeRequest(pr_url="https://github.com/VarshithReddy2006/Repo-Intelligence-Agent/pull/42")
        self.assertEqual(req.owner, "VarshithReddy2006")
        self.assertEqual(req.repo, "Repo-Intelligence-Agent")
        self.assertEqual(req.pr_number, 42)

        req_trail = PRAnalyzeRequest(pr_url="https://github.com/owner/repo/pull/123/")
        self.assertEqual(req_trail.owner, "owner")
        self.assertEqual(req_trail.repo, "repo")
        self.assertEqual(req_trail.pr_number, 123)

    def test_pr_url_parsing_invalid(self):
        """Verifies that invalid PR URLs raise a ValueError."""
        with self.assertRaises(ValueError):
            PRAnalyzeRequest(pr_url="https://github.com/owner/repo")
        with self.assertRaises(ValueError):
            PRAnalyzeRequest(pr_url="https://gitlab.com/owner/repo/pull/42")
        with self.assertRaises(ValueError):
            PRAnalyzeRequest(pr_url="https://github.com/owner/repo/pull/notanumber")

    def test_pr_size_classification(self):
        """Verifies PR size classification boundaries."""
        # XS: file_score = 3, symbol_score = 1.5, line_score = 1 -> score = 5.5
        self.assertEqual(self.service.classify_pr_size(1, 10, 1), "XS")
        
        # S: 21-40. files=5 (15 pts), symbols=10 (15 pts), lines=10 (1 pt) -> 31
        self.assertEqual(self.service.classify_pr_size(5, 10, 10), "S")

        # M: 41-60. files=10 (30 pts), symbols=10 (15 pts), lines=50 (5 pts) -> 50
        self.assertEqual(self.service.classify_pr_size(10, 50, 10), "M")

        # L: 61-80. files=15 (30 pts), symbols=20 (30 pts), lines=100 (10 pts) -> 70
        self.assertEqual(self.service.classify_pr_size(15, 100, 20), "L")

        # XL: 81-100. files=20 (30 pts), symbols=30 (30 pts), lines=400 (40 pts) -> 100
        self.assertEqual(self.service.classify_pr_size(20, 400, 30), "XL")

        # Large lines but small files/symbols
        # files=2 (6 pts), symbols=2 (3 pts), lines=5000 (40 pts) -> 49 (M)
        self.assertEqual(self.service.classify_pr_size(2, 5000, 2), "M")

    def test_blast_radius_classification(self):
        """Verifies blast radius classification and depth promotion."""
        # 0-5 affected files -> LOW
        self.assertEqual(self.service.classify_blast_radius(3, 1), "LOW")
        # 6-15 affected files -> MEDIUM
        self.assertEqual(self.service.classify_blast_radius(8, 1), "MEDIUM")
        # 16-30 affected files -> HIGH
        self.assertEqual(self.service.classify_blast_radius(20, 1), "HIGH")
        # 31+ affected files -> EXTREME
        self.assertEqual(self.service.classify_blast_radius(35, 1), "EXTREME")

        # Depth promotion
        # LOW -> MEDIUM due to depth >= 3
        self.assertEqual(self.service.classify_blast_radius(3, 3), "MEDIUM")
        # MEDIUM -> HIGH due to depth >= 3
        self.assertEqual(self.service.classify_blast_radius(8, 3), "HIGH")
        # HIGH -> EXTREME due to depth >= 3
        self.assertEqual(self.service.classify_blast_radius(20, 3), "EXTREME")
        # EXTREME remains EXTREME
        self.assertEqual(self.service.classify_blast_radius(35, 3), "EXTREME")

    def test_risk_scoring_and_explanations(self):
        """Verifies risk score calculation and top risk sorting/filtering."""
        changed_files = [ChangedFile(filename=f"file{i}.py", status="modified", additions=5, deletions=5, changes=10) for i in range(5)]
        
        # files=5 (8 pts), symbols=10 (5 pts), 1 entry point (15 pts), 1 core (10 pts), impact=3/10 (impact_ratio=0.3 -> 4 pts), depth=3 (7 pts), symbol_removal=5
        score, level, breakdown, top_risks = self.service._compute_risk_and_explanations(
            changed_files=changed_files,
            changed_symbols_count=10,
            changed_entry_points=["file1.py"],
            changed_core_files=["file2.py"],
            changed_high_coupling_files=[],
            impact_radius=3,
            max_depth=3,
            removed_symbols_count=2,
            total_graph_nodes=10
        )
        
        # Expected score: 8 (files) + 5 (symbols) + 10 (core) + 15 (entry) + 4 (impact) + 7 (depth) + 5 (removal) = 54 -> HIGH
        self.assertEqual(score, 54)
        self.assertEqual(level, "HIGH")
        
        # Check top risks: sorted by contribution
        # Entry point (15) > Core module (10) > Changed file count (8) > Dependency depth (7) > Changed symbol count / symbol removal (5)
        self.assertTrue(len(top_risks) <= 5)
        self.assertEqual(top_risks[0], "Entry point modified (file1.py)")
        self.assertEqual(top_risks[1], "Core module modified (file2.py)")
        self.assertEqual(top_risks[2], "Large number of changed files (5)")
        self.assertEqual(top_risks[3], "Deep dependency propagation (depth 3)")
        self.assertTrue("Public symbol removal detected" in top_risks or "Changed symbol count" in top_risks)

    @patch("services.pr_intelligence_service.GitHubService")
    @patch("services.pr_intelligence_service.GraphService")
    @patch("services.pr_intelligence_service.SymbolService")
    @patch("services.pr_intelligence_service.ArchitectureService")
    def test_analyze_pull_request_success(self, mock_arch, mock_symbol, mock_graph, mock_github):
        """Verifies successful PR analysis pipeline run."""
        # Setup mocks
        mock_graph_instance = mock_graph.return_value
        mock_graph_instance.graph_exists.return_value = True
        
        # Create a mock DiGraph
        g = nx.DiGraph()
        g.add_node("services/architecture_service.py")
        g.add_node("backend/api.py")
        g.add_edge("backend/api.py", "services/architecture_service.py")
        mock_graph_instance.load_graph.return_value = g

        mock_symbol_instance = mock_symbol.return_value
        mock_symbol_instance.index_exists.return_value = True
        
        # Create mock symbol index
        mock_sym_index = MagicMock()
        mock_sym_index.symbols = [
            Symbol(name="analyze_change", type="method", file_path="services/architecture_service.py", line_number=42, language="python", parent_class="ArchitectureService")
        ]
        mock_symbol_instance.load.return_value = mock_sym_index

        mock_arch_instance = mock_arch.return_value
        mock_summary = MagicMock()
        mock_summary.core_modules = ["services/architecture_service.py"]
        mock_summary.high_coupling_modules = []
        mock_summary.entry_points = ["backend/api.py"]
        mock_arch_instance.get_summary.return_value = mock_summary

        mock_github_instance = mock_github.return_value
        mock_github_instance.fetch_pull_request_metadata.return_value = {
            "title": "Update architectural service",
            "state": "open",
            "html_url": "https://github.com/VarshithReddy2006/Repo-Intelligence-Agent/pull/1",
            "additions": 20,
            "deletions": 5,
            "head_sha": "abcdef123"
        }
        mock_github_instance.fetch_pull_request_files.return_value = [
            {"filename": "services/architecture_service.py", "status": "modified", "additions": 20, "deletions": 5, "changes": 25}
        ]

        # Run analysis
        service = PRIntelligenceService(
            github_service=mock_github_instance,
            symbol_service=mock_symbol_instance,
            graph_service=mock_graph_instance,
            architecture_service=mock_arch_instance
        )
        res = service.analyze_pull_request("VarshithReddy2006", "Repo-Intelligence-Agent", 1)

        self.assertEqual(res.repo, "VarshithReddy2006/Repo-Intelligence-Agent")
        self.assertEqual(res.pr_number, 1)
        self.assertEqual(res.pr_title, "Update architectural service")
        self.assertEqual(res.pr_size, "XS")
        self.assertEqual(res.risk_level, "LOW")
        self.assertEqual(res.changed_core_files, ["services/architecture_service.py"])
        self.assertEqual(res.impact_radius, 1)
        self.assertEqual(res.affected_files, ["backend/api.py"])
        self.assertEqual(res.max_depth, 1)


class TestPRIntelligenceEndpoints(unittest.TestCase):

    @patch("backend.api.pr_intelligence_service")
    def test_api_pr_analyze_success(self, mock_pr_service):
        """Verifies endpoint returns correct payload on successful analysis."""
        mock_result = {
            "repo": "owner/repo",
            "pr_number": 42,
            "pr_url": "https://github.com/owner/repo/pull/42",
            "pr_title": "Cool PR",
            "pr_state": "open",
            "pr_size": "M",
            "risk_score": 35,
            "risk_level": "MEDIUM",
            "risk_breakdown": [],
            "top_risks": ["Core module modified"],
            "changed_files": [],
            "total_additions": 100,
            "total_deletions": 50,
            "added_symbols": [],
            "modified_symbols": [],
            "removed_symbols": [],
            "affected_files": [],
            "impact_radius": 0,
            "blast_radius": "LOW",
            "max_depth": 0,
            "propagation_paths": [],
            "affected_components": [],
            "changed_entry_points": [],
            "changed_core_files": [],
            "changed_high_coupling_files": [],
            "review_focus_areas": [],
            "analyzed_at": "2026-06-20T12:00:00Z"
        }
        mock_pr_service.analyze_pull_request.return_value = mock_result

        payload = {"pr_url": "https://github.com/owner/repo/pull/42"}
        response = client.post("/api/pr/analyze", json=payload)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["repo"], "owner/repo")
        self.assertEqual(data["pr_number"], 42)
        self.assertEqual(data["risk_level"], "MEDIUM")
        self.assertEqual(data["top_risks"], ["Core module modified"])

    @patch("backend.api.pr_intelligence_service")
    def test_api_pr_analyze_not_indexed(self, mock_pr_service):
        """Verifies endpoint returns 404 if repo is not indexed."""
        mock_pr_service.analyze_pull_request.side_effect = ValueError("No dependency graph found")

        payload = {"pr_url": "https://github.com/owner/repo/pull/42"}
        response = client.post("/api/pr/analyze", json=payload)
        
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "No dependency graph found")

    @patch("backend.api.pr_intelligence_service")
    def test_api_pr_analyze_github_error(self, mock_pr_service):
        """Verifies endpoint returns 502 if GitHub API call fails."""
        mock_pr_service.analyze_pull_request.side_effect = Exception("Rate limit exceeded")

        payload = {"pr_url": "https://github.com/owner/repo/pull/42"}
        response = client.post("/api/pr/analyze", json=payload)
        
        self.assertEqual(response.status_code, 502)
        self.assertTrue("rate limit" in response.json()["detail"].lower())

    @patch("backend.api.github_service")
    @patch("backend.api.graph_service")
    @patch("backend.api.symbol_service")
    def test_api_pr_health(self, mock_symbol, mock_graph, mock_github):
        """Verifies health diagnostics endpoint."""
        mock_github.get_rate_limit_info.return_value = {"remaining": 4500, "reset": 12345678}
        mock_graph.graph_exists.return_value = True
        mock_symbol.index_exists.return_value = False

        response = client.get("/api/pr/health?owner=owner&repo=repo")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue("github_token" in data)
        self.assertEqual(data["rate_limit_remaining"], 4500)
        self.assertEqual(data["graph_available"], True)
        self.assertEqual(data["symbol_index_available"], False)
        self.assertEqual(data["status"], "healthy")
