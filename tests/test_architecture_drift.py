import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api import app
from models.architecture_drift import PRDriftRequest, DependencyEdge, CouplingChange
from services.architecture_drift_service import ArchitectureDriftService
import networkx as nx

client = TestClient(app)


class TestPRDriftModels(unittest.TestCase):
    def test_request_parsing_url(self):
        """Covers valid URL parsing."""
        req = PRDriftRequest(pr_url="https://github.com/owner/repo/pull/100")
        self.assertEqual(req.owner, "owner")
        self.assertEqual(req.repo, "repo")
        self.assertEqual(req.pr_number, 100)

        # Trail slash
        req2 = PRDriftRequest(pr_url="https://github.com/owner/repo/pull/100/")
        self.assertEqual(req2.pr_number, 100)

    def test_request_parsing_coords(self):
        """Covers structured coords."""
        req = PRDriftRequest(owner="owner", repo="repo", pr_number=100)
        self.assertEqual(req.owner, "owner")
        self.assertEqual(req.repo, "repo")
        self.assertEqual(req.pr_number, 100)

    def test_request_parsing_invalid(self):
        """Covers malformed URL formats raising validation error."""
        with self.assertRaises(ValueError):
            PRDriftRequest(pr_url="https://github.com/owner/repo")
        with self.assertRaises(ValueError):
            PRDriftRequest(pr_url="https://gitlab.com/owner/repo/pull/12")
        with self.assertRaises(ValueError):
            PRDriftRequest(pr_url="https://github.com/owner/repo/pull/notanumber")


class TestArchitectureDriftAlgorithms(unittest.TestCase):
    def setUp(self):
        self.service = ArchitectureDriftService()

    def test_canonical_cycle_rotation(self):
        """Covers that rotated cycle lists resolve to the same canonical tuple."""
        c1 = ["A", "B", "C"]
        c2 = ["B", "C", "A"]
        c3 = ["C", "A", "B"]
        self.assertEqual(self.service._canonical_cycle(c1), ("A", "B", "C"))
        self.assertEqual(self.service._canonical_cycle(c2), ("A", "B", "C"))
        self.assertEqual(self.service._canonical_cycle(c3), ("A", "B", "C"))

    def test_canonical_cycle_empty(self):
        """Covers empty list handling."""
        self.assertEqual(self.service._canonical_cycle([]), ())

    def test_get_cycles_limited(self):
        """Covers cycles extraction with limit safeguarding."""
        g = nx.DiGraph()
        # Create a highly cyclic graph
        g.add_edge("A", "B")
        g.add_edge("B", "A")
        g.add_edge("B", "C")
        g.add_edge("C", "B")

        cycles = self.service._get_cycles(g, limit=1)
        self.assertEqual(len(cycles), 1)

    def test_is_entry_point_file(self):
        """Covers entry point file detection conventions."""
        self.assertTrue(self.service._is_entry_point_file("main.py", []))
        self.assertTrue(self.service._is_entry_point_file("App.tsx", []))
        self.assertTrue(self.service._is_entry_point_file("app/routes/user.py", []))
        self.assertTrue(self.service._is_entry_point_file("backend/app.py", []))
        # FastAPI import
        self.assertTrue(
            self.service._is_entry_point_file("some_module.py", ["fastapi"])
        )
        self.assertFalse(
            self.service._is_entry_point_file("some_module.py", ["requests"])
        )

    def test_compute_drift_risk(self):
        """Covers risk score weights and level boundaries."""
        # 1. No risk factors -> 0
        score, level = self.service._compute_drift_risk(
            new_cycles=[],
            changed_core_files=[],
            new_entry_points=[],
            coupling_increase=[],
            blast_radius_level="LOW",
            added_dependencies=[],
            removed_entry_points=[],
        )
        self.assertEqual(score, 0)
        self.assertEqual(level, "LOW")

        # 2. Cycles added -> 45
        score, level = self.service._compute_drift_risk(
            new_cycles=[["A", "B"]],
            changed_core_files=[],
            new_entry_points=[],
            coupling_increase=[],
            blast_radius_level="LOW",
            added_dependencies=[],
            removed_entry_points=[],
        )
        self.assertEqual(score, 45)
        self.assertEqual(level, "MEDIUM")

        # 3. Core module modified (15) + entry point added (10) -> 25
        score, level = self.service._compute_drift_risk(
            new_cycles=[],
            changed_core_files=["core.py"],
            new_entry_points=["main.py"],
            coupling_increase=[],
            blast_radius_level="LOW",
            added_dependencies=[],
            removed_entry_points=[],
        )
        self.assertEqual(score, 25)
        self.assertEqual(level, "LOW")

        # 4. Cycle (45) + core (15) + entry (10) + coupling (15) + blast (15) + edge (10) -> 110 (capped at 100)
        score, level = self.service._compute_drift_risk(
            new_cycles=[["A", "B"]],
            changed_core_files=["core.py"],
            new_entry_points=["main.py"],
            coupling_increase=[CouplingChange(file="core.py", before=5, after=12)],
            blast_radius_level="HIGH",
            added_dependencies=[DependencyEdge(source="A", target="B")],
            removed_entry_points=[],
        )
        self.assertEqual(score, 100)
        self.assertEqual(level, "CRITICAL")

    def test_compute_drift_improvement(self):
        """Covers improvement score weights."""
        # 1. Resolved cycle (45) + coupling decrease (20) -> 65
        score = self.service._compute_drift_improvement(
            resolved_cycles=[["A", "B"]],
            coupling_decrease=[CouplingChange(file="core.py", before=12, after=6)],
            removed_entry_points=[],
            removed_dependencies=[],
            total_additions=0,
            total_deletions=0,
        )
        self.assertEqual(score, 65)

        # 2. Entry point removed (15) + dependency removed (10) -> 25
        score = self.service._compute_drift_improvement(
            resolved_cycles=[],
            coupling_decrease=[],
            removed_entry_points=["main.py"],
            removed_dependencies=[DependencyEdge(source="A", target="B")],
            total_additions=0,
            total_deletions=0,
        )
        self.assertEqual(score, 25)

        # 3. Size reduction (10) (deletions > additions by >= 50 lines)
        score = self.service._compute_drift_improvement(
            resolved_cycles=[],
            coupling_decrease=[],
            removed_entry_points=[],
            removed_dependencies=[],
            total_additions=10,
            total_deletions=65,
        )
        self.assertEqual(score, 10)

    def test_compute_drift_categories(self):
        """Covers drift categories badges mapping."""
        cats = self.service._compute_drift_categories(
            new_cycles=[["A", "B"]],
            resolved_cycles=[["C", "D"]],
            coupling_increase=[CouplingChange(file="A", before=2, after=8)],
            coupling_decrease=[],
            new_entry_points=["main.py"],
            removed_entry_points=[],
            added_dependencies=[],
            removed_dependencies=[],
        )
        self.assertTrue("CYCLE_INTRODUCED" in cats)
        self.assertTrue("CYCLE_RESOLVED" in cats)
        self.assertTrue("COUPLING_INCREASED" in cats)
        self.assertTrue("ENTRY_POINT_ADDED" in cats)

    def test_generate_top_findings(self):
        """Covers findings generation limits and priority."""
        findings = self.service._generate_top_findings(
            new_cycles=[["A", "B"]],
            resolved_cycles=[],
            new_entry_points=["main.py"],
            removed_entry_points=[],
            coupling_increase=[CouplingChange(file="core.py", before=2, after=8)],
            coupling_decrease=[],
            added_dependencies=[DependencyEdge(source="A", target="B")],
            removed_dependencies=[],
            impact_radius=18,
        )
        self.assertTrue(len(findings) <= 10)
        self.assertEqual(findings[0], "New dependency cycle introduced: A -> B -> A")
        self.assertEqual(findings[1], "New entry point created: main.py")
        self.assertEqual(
            findings[2], "Coupling increased significantly in core.py (from 2 to 8)"
        )

    @patch("services.architecture_drift_service.GitHubService")
    @patch("services.architecture_drift_service.GraphService")
    @patch("services.architecture_drift_service.ArchitectureService")
    @patch("services.architecture_drift_service.TreeSitterService")
    def test_analyze_drift_success(self, mock_ts, mock_arch, mock_graph, mock_github):
        """Covers complete drift analysis pipeline execution."""
        mock_graph_instance = mock_graph.return_value
        mock_graph_instance.graph_exists.return_value = True

        # Baseline graph
        g = nx.DiGraph()
        g.add_edge("backend/api.py", "services/architecture_service.py")
        mock_graph_instance.load_graph.return_value = g

        mock_arch_instance = mock_arch.return_value
        mock_summary = MagicMock()
        mock_summary.core_modules = ["services/architecture_service.py"]
        mock_summary.high_coupling_modules = []
        mock_summary.entry_points = ["backend/api.py"]
        mock_arch_instance.get_summary.return_value = mock_summary

        mock_github_instance = mock_github.return_value
        mock_github_instance.fetch_pull_request_metadata.return_value = {
            "title": "Introduce drift cycle",
            "state": "open",
            "html_url": "https://github.com/owner/repo/pull/1",
            "additions": 30,
            "deletions": 5,
            "head_sha": "abcdef123",
        }
        mock_github_instance.fetch_pull_request_files.return_value = [
            {
                "filename": "services/architecture_service.py",
                "status": "modified",
                "additions": 30,
                "deletions": 5,
                "changes": 35,
            }
        ]
        # Content fetch mock
        mock_github_instance.fetch_file_content.return_value = "import backend.api"

        # TreeSitter mock: new imports introduced (now architecture_service imports api.py back -> CYCLE!)
        mock_ts_instance = mock_ts.return_value
        mock_ts_instance.parse_file.return_value = {
            "file_path": "services/architecture_service.py",
            "language": "python",
            "imports": ["backend.api"],
        }

        # Setup resolution to backend/api.py
        mock_graph._resolve_import = MagicMock(return_value="backend/api.py")
        # Run service
        drift_service = ArchitectureDriftService(
            github_service=mock_github_instance,
            graph_service=mock_graph_instance,
            architecture_service=mock_arch_instance,
        )
        drift_service.tree_sitter = mock_ts_instance

        res = drift_service.analyze_drift("owner", "repo", 1)

        self.assertEqual(res.repo, "owner/repo")
        self.assertEqual(res.pr_number, 1)
        self.assertTrue(res.architecture_risk_score > 0)
        self.assertEqual(res.architecture_risk_level, "HIGH")
        self.assertEqual(len(res.new_cycles), 1)
        # Cycle is backend/api.py <-> services/architecture_service.py
        self.assertTrue("backend/api.py" in res.new_cycles[0])
        self.assertTrue("services/architecture_service.py" in res.new_cycles[0])
        self.assertEqual(len(res.added_dependencies), 1)
        self.assertEqual(
            res.added_dependencies[0].source, "services/architecture_service.py"
        )
        self.assertEqual(res.added_dependencies[0].target, "backend/api.py")


class TestPRDriftEndpoints(unittest.TestCase):
    @patch("backend.api.architecture_drift_service")
    def test_endpoint_drift_analyze_success(self, mock_drift):
        """Covers successful drift analysis HTTP response."""
        mock_res = {
            "repo": "owner/repo",
            "pr_number": 42,
            "architecture_risk_score": 60,
            "architecture_risk_level": "HIGH",
            "architecture_improvement_score": 0,
            "top_findings": ["New dependency cycle introduced"],
            "drift_categories": ["CYCLE_INTRODUCED"],
            "architectural_hotspots": ["backend/api.py"],
            "added_dependencies": [],
            "removed_dependencies": [],
            "new_cycles": [],
            "resolved_cycles": [],
            "coupling_increase": [],
            "coupling_decrease": [],
            "new_entry_points": [],
            "removed_entry_points": [],
            "analyzed_at": "2026-06-20T12:00:00Z",
        }
        mock_drift.analyze_drift.return_value = mock_res

        response = client.post(
            "/api/architecture/drift",
            json={"pr_url": "https://github.com/owner/repo/pull/42"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["repo"], "owner/repo")
        self.assertEqual(data["architecture_risk_score"], 60)
        self.assertEqual(data["top_findings"], ["New dependency cycle introduced"])
        self.assertEqual(data["architectural_hotspots"], ["backend/api.py"])

    @patch("backend.api.architecture_drift_service")
    def test_endpoint_drift_analyze_not_indexed(self, mock_drift):
        """Covers 404 for unindexed repos."""
        mock_drift.analyze_drift.side_effect = ValueError("No dependency graph found")

        response = client.post(
            "/api/architecture/drift",
            json={"pr_url": "https://github.com/owner/repo/pull/42"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "No dependency graph found")
