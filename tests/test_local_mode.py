"""Tests for nexusobserve local mode (JSONL store + console summary)."""

import json
import os

import pytest
import nexusobserve


def _make_record(run_id: str = "t-run"):
    return nexusobserve.record_decision(
        run_id=run_id,
        context={"order_id": "ORD-0001"},
        chosen={"action": "full_refund", "cost": 500.0},
        alternatives=[
            {"action": "escalate",    "cost": 120.0},
            {"action": "deny+coupon", "cost":  30.0},
        ],
        latency_ms=5.0,
    )


def test_local_mode_saves_jsonl(tmp_path, monkeypatch):
    jsonl = tmp_path / "decisions.jsonl"
    monkeypatch.setenv("NEXUSOBSERVE_LOCAL_PATH", str(jsonl))

    nexusobserve.init(local=True)
    rec = _make_record()

    assert jsonl.exists(), "JSONL file not created"
    saved = json.loads(jsonl.read_text().strip())
    assert saved["run_id"] == "t-run"
    assert saved["chosen"]["action"] == "full_refund"
    assert saved["decision_id"] == rec.decision_id


def test_local_mode_prints_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NEXUSOBSERVE_LOCAL_PATH", str(tmp_path / "d.jsonl"))

    nexusobserve.init(local=True)
    _make_record()

    out = capsys.readouterr().out
    assert "full_refund" in out
    assert "escalate" in out
    assert "opp_cost=-380" in out
    assert "opp_cost=-470" in out


def test_env_var_activates_local_mode(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NEXUSOBSERVE_LOCAL", "1")
    monkeypatch.setenv("NEXUSOBSERVE_LOCAL_PATH", str(tmp_path / "env.jsonl"))

    # No init() call — env var alone should activate
    _make_record(run_id="env-run")

    out = capsys.readouterr().out
    assert "env-run" in out


def test_server_mode_not_triggered_in_local_mode(tmp_path, monkeypatch, capsys):
    """record_decision with local=True must NOT attempt a server POST."""
    monkeypatch.setenv("NEXUSOBSERVE_LOCAL_PATH", str(tmp_path / "no-server.jsonl"))

    nexusobserve.init(local=True)
    # Pass a server_url that would cause a connection error if called
    rec = nexusobserve.record_decision(
        run_id="local-only",
        context={},
        chosen={"action": "x", "cost": 1.0},
        alternatives=[],
        latency_ms=1.0,
        server_url="http://127.0.0.1:19999",  # nothing listening here
    )
    # If server was called, stderr would contain WARNING; stdout has the summary
    captured = capsys.readouterr()
    assert "WARNING" not in captured.err
    assert rec.run_id == "local-only"


def test_cli_show(tmp_path, monkeypatch, capsys):
    """python -m nexusobserve show lists recorded decisions."""
    jsonl = tmp_path / "cli.jsonl"
    monkeypatch.setenv("NEXUSOBSERVE_LOCAL_PATH", str(jsonl))

    nexusobserve.init(local=True)
    _make_record(run_id="cli-run")
    capsys.readouterr()  # discard record_decision output

    # Run the CLI
    from nexusobserve.__main__ import _show
    _show()

    out = capsys.readouterr().out
    assert "cli-run" in out
    assert "full_refund" in out
    assert "opp_cost=-380" in out


def test_cli_show_empty(tmp_path, monkeypatch, capsys):
    """python -m nexusobserve show on empty store gives a helpful message."""
    monkeypatch.setenv("NEXUSOBSERVE_LOCAL_PATH", str(tmp_path / "empty.jsonl"))

    from nexusobserve.__main__ import _show
    _show()

    out = capsys.readouterr().out
    assert "No decisions" in out
