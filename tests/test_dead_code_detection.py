import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import networkx as nx
from fastapi.testclient import TestClient

from backend.api import app
from models.dead_code import (
    DeadCodeRequest,
    DeadFile,
    OrphanModule,
    DeadDependencyChain,
)
from services.dead_code_service import DeadCodeService

client = TestClient(app)


class TestDeadCodeModels(unittest.TestCase):
    def test_model_instantiation(self):
        """Verifies Pydantic schemas serialize and validate correctly."""
        df = DeadFile(
            file_path="old/utils.py",
            confidence=0.95,
            risk_level="SAFE",
            recommendation="Remove it",
        )
        self.assertEqual(df.file_path, "old/utils.py")
        self.assertEqual(df.confidence, 0.95)

        om = OrphanModule(
            file_path="old/auth.py",
            confidence=0.90,
            risk_level="REVIEW",
            recommendation="Review it",
            last_reachable_parent="services/auth.py",
        )
        self.assertEqual(om.last_reachable_parent, "services/auth.py")

        chain = DeadDependencyChain(
            chain=["a.py", "b.py"],
            confidence=0.95,
            risk_level="SAFE",
            recommendation="Clean chain",
            length=1,
            total_nodes=2,
            max_centrality=0.15,
        )
        self.assertEqual(chain.length, 1)

        req = DeadCodeRequest(owner="owner", repo="repo")
        self.assertEqual(req.owner, "owner")


class TestDeadCodeAlgorithms(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.close()
        self.service = DeadCodeService(scores_file_path=self.temp_file.name)

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_is_ignored(self):
        """Covers default and custom directory/file ignore pattern matching."""
        patterns = ["migrations/", "legacy/", "*.md", "temp_*"]
        self.assertTrue(self.service.is_ignored("src/migrations/001_init.py", patterns))
        self.assertTrue(self.service.is_ignored("legacy/auth.py", patterns))
        self.assertTrue(self.service.is_ignored("README.md", patterns))
        self.assertTrue(self.service.is_ignored("temp_helper.py", patterns))
        self.assertFalse(self.service.is_ignored("src/services/auth.py", patterns))

    def test_load_ignore_patterns_custom(self):
        """Covers parsing custom ignore list from data/dead_code_ignore.json."""
        custom_data = ["test_custom/"]
        with patch(
            "builtins.open", unittest.mock.mock_open(read_data=json.dumps(custom_data))
        ):
            with patch("os.path.exists", return_value=True):
                patterns = self.service.load_ignore_patterns()
                self.assertIn("test_custom/", patterns)
                self.assertIn("migrations/", patterns)  # default is preserved

    def test_find_last_reachable_parent(self):
        """Covers closest parent resolution using undirected graph traversal."""
        g = nx.DiGraph()
        # Reachable component
        g.add_edge("main.py", "services/auth_service.py")
        g.add_edge("services/auth_service.py", "utils/logger.py")

        # Unreachable orphaned component
        g.add_edge("legacy/auth.py", "legacy/crypto.py")

        # Connection in undirected graph (e.g. legacy/auth.py imports utils/logger.py)
        g.add_edge("legacy/auth.py", "utils/logger.py")

        reachable = {"main.py", "services/auth_service.py", "utils/logger.py"}

        parent = self.service._find_last_reachable_parent(
            g, "legacy/crypto.py", reachable
        )
        # legacy/crypto.py -> legacy/auth.py -> utils/logger.py
        self.assertEqual(parent, "utils/logger.py")

        # Completely disconnected
        g.remove_edge("legacy/auth.py", "utils/logger.py")
        parent_none = self.service._find_last_reachable_parent(
            g, "legacy/crypto.py", reachable
        )
        self.assertIsNone(parent_none)

    def test_find_dead_chains(self):
        """Covers components path extraction for dead chains."""
        g = nx.DiGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        g.add_edge("D", "E")  # Another isolated component

        centrality = {"A": 0.1, "B": 0.2, "C": 0.3, "D": 0.05, "E": 0.08}

        chains = self.service._find_dead_chains(g, centrality)
        # We expect two chains: [A, B, C] and [D, E]
        self.assertEqual(len(chains), 2)

        # Verify attributes on first chain
        c1 = [c for c in chains if "A" in c.chain][0]
        self.assertEqual(c1.length, 2)
        self.assertEqual(c1.total_nodes, 3)
        self.assertEqual(c1.max_centrality, 0.3)

    def test_persistence_scores(self):
        """Covers saving and loading historical scores in json storage."""
        self.service._save_new_score("owner/repo", 85)
        prev = self.service._load_previous_score("owner/repo")
        self.assertEqual(prev, 85)

        # Score for missing repo
        self.assertIsNone(self.service._load_previous_score("owner/other"))

    @patch("services.dead_code_service.GitHubService")
    @patch("services.dead_code_service.GraphService")
    @patch("services.dead_code_service.ArchitectureService")
    def test_analyze_dead_code_pipeline(self, mock_arch, mock_graph, mock_github):
        """Covers complete dead code reachability and graph-weighted scoring analysis pipeline."""
        mock_graph_instance = mock_graph.return_value
        mock_graph_instance.graph_exists.return_value = True

        g = nx.DiGraph()
        # Reachable
        g.add_edge("main.py", "active_service.py")
        # Unreachable Unused file (in_degree = 0)
        g.add_node("dead_root.py")
        # Unreachable Orphan module (in_degree > 0)
        g.add_edge("dead_root.py", "dead_child.py")

        mock_graph_instance.load_graph.return_value = g

        mock_arch_instance = mock_arch.return_value
        mock_summary = MagicMock()
        mock_summary.entry_points = ["main.py"]
        mock_arch_instance.get_summary.return_value = mock_summary

        service = DeadCodeService(
            github_service=mock_github.return_value,
            graph_service=mock_graph.return_value,
            architecture_service=mock_arch.return_value,
            scores_file_path=self.temp_file.name,
        )
        res = service.analyze_dead_code("owner", "repo")

        self.assertEqual(res.repo, "owner/repo")
        self.assertTrue(res.cleanup_score < 100)
        self.assertEqual(len(res.unused_files), 1)
        self.assertEqual(res.unused_files[0].file_path, "dead_root.py")

        self.assertEqual(len(res.orphan_modules), 1)
        self.assertEqual(res.orphan_modules[0].file_path, "dead_child.py")

        # Verification of chain extraction
        self.assertEqual(len(res.dead_dependency_chains), 1)
        self.assertEqual(
            res.dead_dependency_chains[0].chain, ["dead_root.py", "dead_child.py"]
        )

        self.assertEqual(
            res.estimated_cleanup_effort, "MEDIUM"
        )  # 1 unused + 1 orphan + 1 chain = 3 findings
        self.assertTrue(len(res.cleanup_recommendations) > 0)


class TestDeadCodeEndpoints(unittest.TestCase):
    @patch("backend.api.dead_code_service")
    def test_endpoint_dead_code_analyze_success(self, mock_service):
        """Covers successful dead code analysis HTTP response."""
        mock_res = {
            "repo": "owner/repo",
            "cleanup_score": 90,
            "previous_cleanup_score": None,
            "estimated_cleanup_effort": "LOW",
            "unused_files": [],
            "orphan_modules": [],
            "dead_dependency_chains": [],
            "cleanup_recommendations": [],
            "analyzed_at": "2026-06-20T12:00:00Z",
        }
        mock_service.analyze_dead_code.return_value = mock_res

        response = client.post(
            "/api/dead-code/analyze", json={"owner": "owner", "repo": "repo"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["cleanup_score"], 90)
        self.assertEqual(data["repo"], "owner/repo")

    @patch("backend.api.dead_code_service")
    def test_endpoint_dead_code_analyze_not_indexed(self, mock_service):
        """Covers 404 for unindexed repositories."""
        mock_service.analyze_dead_code.side_effect = ValueError(
            "No dependency graph found"
        )

        response = client.post(
            "/api/dead-code/analyze", json={"owner": "owner", "repo": "repo"}
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "No dependency graph found")
