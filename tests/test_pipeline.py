"""Tests for the LangGraph prospection pipeline."""

import pytest
from prospection_graph.graph import build_graph, run_prospect, run_batch
from prospection_graph.tools import generate_email_patterns, hunter_verify
from prospection_graph import nodes
from prospection_graph.state import ProspectState


class TestEmailPatterns:
    def test_dr_pattern(self):
        patterns = generate_email_patterns("Dr. Martin Dupont")
        assert "dr.dupont@gmail.com" in patterns
    
    def test_with_domain(self):
        patterns = generate_email_patterns("Martin Dupont", "cabinet-dupont.fr")
        assert "contact@cabinet-dupont.fr" in patterns
    
    def test_empty_name(self):
        patterns = generate_email_patterns("Dr.")
        assert patterns == []


class TestHunterVerify:
    def test_dr_pattern_scores_high(self):
        result = hunter_verify("dr.dupont@gmail.com")
        assert result["score"] > 80
    
    def test_random_email_scores_low(self):
        result = hunter_verify("random@test.com")
        assert result["score"] < 80


class TestGraphStructure:
    def test_graph_builds(self):
        graph = build_graph()
        assert graph is not None
    
    def test_graph_compiles(self):
        graph = build_graph()
        compiled = graph.compile()
        assert compiled is not None
    
    def test_graph_has_all_nodes(self):
        graph = build_graph()
        compiled = graph.compile()
        node_names = set(compiled.get_graph().nodes.keys())
        expected = {"scrape", "enrich", "verify_email", "search_linkedin",
                    "draft_email", "draft_linkedin", "send", "update_crm", "no_channel"}
        assert expected.issubset(node_names)


class TestFullPipeline:
    def test_prospect_with_email(self):
        """Prospect with valid email → should send email."""
        result = run_prospect("Dr. Martin Dupont", "Paris", "dentiste")
        assert result["status"] == "contacted"
        assert result["channel"] == "email"
        assert result["message_sent"] == True
        assert result["crm_updated"] == True
    
    def test_steps_are_logged(self):
        result = run_prospect("Dr. Martin Dupont", "Paris")
        assert len(result["steps_log"]) > 0
        assert any("scraped" in s for s in result["steps_log"])
        assert any("CRM" in s for s in result["steps_log"])
    
    def test_email_is_verified(self):
        result = run_prospect("Dr. Martin Dupont", "Paris")
        assert result["email_score"] > 80
        assert result["email_verified"] == True


class TestBatch:
    def test_batch_processing(self):
        prospects = [
            {"name": "Dr. Dupont", "city": "Paris"},
            {"name": "Dr. Martin", "city": "Lyon"},
        ]
        results = run_batch(prospects)
        assert len(results) == 2
        assert all(r["crm_updated"] for r in results)
    
    def test_batch_respects_daily_limit(self):
        prospects = [{"name": f"Dr. Test{i}", "city": "Paris"} for i in range(30)]
        results = run_batch(prospects, max_per_day=5)
        emails_sent = sum(1 for r in results if r.get("channel") == "email" and r["message_sent"])
        assert emails_sent <= 5


class TestAPI:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from main import app
        return TestClient(app)
    
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["framework"] == "LangGraph"
    
    def test_graph_endpoint(self, client):
        r = client.get("/graph")
        assert r.status_code == 200
        assert "nodes" in r.json()
    
    def test_process_prospect(self, client):
        r = client.post("/prospect", json={
            "name": "Dr. Dupont",
            "city": "Paris",
            "sector": "dentiste",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "contacted"
    
    def test_process_batch(self, client):
        r = client.post("/batch", json={
            "prospects": [
                {"name": "Dr. A", "city": "Paris"},
                {"name": "Dr. B", "city": "Lyon"},
            ],
            "max_per_day": 25,
        })
        assert r.status_code == 200
        assert r.json()["summary"]["total"] == 2
