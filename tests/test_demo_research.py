"""Pure research facts, independent boundaries and the captured legacy baseline."""
from copy import deepcopy
from datetime import timedelta, timezone
import ast
import builtins
import hashlib
import json
from pathlib import Path
import socket

import pytest
from pydantic import ValidationError

from jarvis import betting_demo as core, demo_research as research, odds_lab, db
from jarvis.odds_lab import Snapshot, digest

GOLDEN = Path(__file__).parent / "fixtures/betting_demo_v1_golden.json"


def data(observation=None, rules=None):
    frozen = json.loads(GOLDEN.read_text(encoding="utf-8"))["frozen"]
    return research.make_input(Snapshot.model_validate(observation or frozen["observations"][0]),
                               rules or frozen["rules"], deepcopy(research.RESEARCH_POLICY))


def test_captured_v1_is_still_exactly_the_unmodified_core():
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    # Canonical content pin is independent of Git/Windows newline conversion.
    canonical = json.dumps(golden, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    assert hashlib.sha256(canonical.encode("utf-8")).hexdigest() == "6b6ce470c0409dac40674a4e6b82e6b608a98ee150a3dde59b3ea86a9d514143"
    assert core.build_scenario() == golden["frozen"]
    assert core.analyze_scenario(core.analysis_input(golden["frozen"])) == golden["analysis"]
    assert golden["final_summary"]["capital_ore"] == 100810
    assert golden["analysis"]["total_stake_ore"] == 4000


def test_standard_research_has_literal_source_counts_and_no_invented_context():
    frozen = core.build_scenario()
    packets = [research.build_packet(data(observation)) for observation in frozen["observations"]]
    assert [p.fresh_count for p in packets] == [4, 4, 4, 4, 0, 3, 4]
    assert [s.age_seconds for s in packets[4].sources] == [300, 300, 300, 300]
    assert packets[4].rejections == ("INSUFFICIENT_FRESH_SOURCES",)
    assert packets[5].rejections == ("INSUFFICIENT_FRESH_SOURCES",)
    assert packets[6].rejections == ()  # Price selection remains the analyst's job.
    for packet in packets:
        assert packet.missing_context == ("form", "injuries", "lineups")
        assert packet.source_independence == "unverified"
        assert packet.data_kind == "synthetic_demo"
        assert packet.notice == research.NOTICE
        assert packet.packet_hash == digest(packet.model_dump(mode="json", exclude={"packet_hash"}))


@pytest.mark.parametrize("age,fresh", [(0, True), (120, True), (120.000001, False), (-0.000001, False)])
def test_freshness_boundary_and_future_quote(age, fresh):
    sample = data()
    value = sample.observation.model_dump(mode="python")
    value["quotes"][0]["updated_at"] = sample.as_of - timedelta(seconds=age)
    packet = research.build_packet(data(value))
    assert packet.sources[0].fresh is fresh
    assert (packet.sources[0].reason is None) is fresh
    assert packet.sources[0].reason == (None if fresh else "FUTURE_QUOTE" if age < 0 else "STALE_QUOTE")
    assert packet.fresh_count == (4 if fresh else 3)


@pytest.mark.parametrize("seconds_after", [0, 1])
def test_started_match_is_rejected_and_as_of_cannot_float_away_from_capture(seconds_after):
    sample = data()
    value = sample.observation.model_dump(mode="python")
    value["starts_at"] = sample.as_of - timedelta(seconds=seconds_after)
    assert "KICKOFF_PASSED" in research.build_packet(data(value)).rejections
    with pytest.raises(ValidationError, match="fångsttid"):
        research.ResearchInput.model_validate({**sample.model_dump(), "as_of": sample.as_of + timedelta(seconds=1)})


@pytest.mark.parametrize("field", ["settlement_data", "result", "home_score", "simulated_finished_at"])
def test_future_fields_cannot_cross_research_input(field):
    with pytest.raises(ValidationError, match="Extra inputs"):
        research.ResearchInput.model_validate({**data().model_dump(), field: {"secret": 9}})


@pytest.mark.parametrize("location", ["observation", "quote"])
@pytest.mark.parametrize("field", ["settlement_data", "result", "home_score"])
def test_nested_future_fields_are_rejected_by_existing_snapshot_contract(location, field):
    value = data().model_dump(mode="json")
    target = value["observation"] if location == "observation" else value["observation"]["quotes"][0]
    target[field] = {"secret": 99}
    with pytest.raises(ValidationError, match="Extra inputs"):
        research.ResearchInput.model_validate(value)


def test_future_outcomes_do_not_change_packets_and_input_is_not_mutated():
    frozen = core.build_scenario()
    before = deepcopy(frozen)
    packets = [research.build_packet(data(o)).model_dump(mode="json") for o in frozen["observations"]]
    for result in frozen["settlement_data"].values():
        result.update(home_score=99, away_score=98)
    again = [research.build_packet(data(o)).model_dump(mode="json") for o in frozen["observations"]]
    assert again == packets
    assert frozen["observations"] == before["observations"]
    assert all(key not in json.dumps(packets) for key in ("home_score", "away_score", "settlement_data", "simulated_finished_at"))


def test_no_clock_network_or_database_and_globals_cannot_change_frozen_input(monkeypatch):
    sample = data()
    frozen_rules = deepcopy(core.build_scenario()["rules"])
    before = sample.model_dump(mode="json")
    expected = research.build_packet(sample)
    def forbidden(*args, **kwargs):
        raise AssertionError("Pure research tried an external effect")
    class ClockTrap:
        now = staticmethod(forbidden)
        utcnow = staticmethod(forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(db, "now", forbidden)
    monkeypatch.setattr(db, "connect", forbidden)
    monkeypatch.setattr(odds_lab, "datetime", ClockTrap)
    monkeypatch.setitem(odds_lab.POLICY, "max_quote_age_seconds", 0)
    rebuilt = research.make_input(sample.observation, frozen_rules, deepcopy(research.RESEARCH_POLICY))
    with monkeypatch.context() as pure:
        pure.setattr(builtins, "open", forbidden)
        assert research.build_packet(rebuilt) == expected == research.build_packet(sample)
    assert sample.model_dump(mode="json") == before


def test_packet_tampering_unknown_version_and_wrong_contract_are_rejected():
    packet = research.build_packet(data())
    value = packet.model_dump(mode="json")
    value["sources"][0]["source_url"] = "https://example.invalid/changed"
    with pytest.raises(ValidationError, match="innehållshash"):
        research.ResearchPacket.model_validate(value)
    with pytest.raises(ValidationError):
        research.ResearchInput.model_validate({**data().model_dump(), "research_version": "future-v99"})
    with pytest.raises(ValidationError, match="kontexttyper"):
        research.ResearchRules.model_validate({**research.RESEARCH_POLICY, "required_context": ["form"]})
    with pytest.raises(ValidationError):
        packet.fresh_count = 0
    with pytest.raises(ValidationError):
        research.ResearchPacket.model_validate({**packet.model_dump(mode="json"), "research_version": "future-v99"})


def test_reshashed_wrong_freshness_reason_still_fails():
    sample = data()
    value = sample.observation.model_dump(mode="python")
    value["quotes"][0]["updated_at"] = sample.as_of + timedelta(seconds=1)
    packet = research.build_packet(data(value)).model_dump(mode="json")
    packet["sources"][0]["reason"] = "STALE_QUOTE"
    packet["packet_hash"] = digest({k: v for k, v in packet.items() if k != "packet_hash"})
    with pytest.raises(ValidationError, match="offertkontroll"):
        research.ResearchPacket.model_validate(packet)


def test_same_instant_as_of_uses_the_exact_capture_representation():
    sample = data()
    offset = sample.as_of.astimezone(timezone(timedelta(hours=2)))
    equivalent = research.ResearchInput.model_validate({**sample.model_dump(), "as_of": offset})
    assert equivalent.as_of.isoformat() == sample.observation.captured_at.isoformat()
    assert research.build_packet(equivalent) == research.build_packet(sample)


def test_research_imports_and_clock_calls_are_explicitly_limited():
    tree = ast.parse(Path(research.__file__).read_text(encoding="utf-8"))
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert imports <= {"typing", "pydantic", "odds_lab"}
    assert not any(isinstance(node, ast.Import) for node in ast.walk(tree))
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and node.func.attr in {"now", "utcnow", "open", "read_text", "write_text", "connect"}
                   for node in ast.walk(tree))
