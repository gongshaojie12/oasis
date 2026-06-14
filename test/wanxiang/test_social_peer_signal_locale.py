# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
"""P4: format_peer_signal + per_focal_peer_signal locale support."""
from __future__ import annotations

from wanxiang.simulation.aggregate import AggregateReport
from wanxiang.simulation.decision import DecisionResult
from wanxiang.simulation.scenario import DecisionKind
from wanxiang.simulation.social import (format_peer_signal,
                                          per_focal_peer_signal)
from wanxiang.social_graph.graph import FriendGraph


def _rate_report():
    return AggregateReport(
        kind=DecisionKind.RATE, n_total=10, n_valid=10,
        error_count=0, error_rate=0.0,
        stats={"mean": 6.7, "median": 7, "p25": 5, "p75": 8, "min": 1, "max": 10})


def _choose_report():
    return AggregateReport(
        kind=DecisionKind.CHOOSE, n_total=10, n_valid=10,
        error_count=0, error_rate=0.0,
        stats={"counts": {"A": 6, "B": 4},
               "share": {"A": 0.6, "B": 0.4}, "top": "A"})


def test_format_peer_signal_defaults_to_zh():
    sig = format_peer_signal(_rate_report())
    assert "均值" in sig or "群体" in sig
    # No English keywords leaked
    assert "mean" not in sig.lower()


def test_format_peer_signal_en_rate_uses_english_phrases():
    sig = format_peer_signal(_rate_report(), locale="en")
    assert "mean" in sig.lower()
    assert "6.7" in sig
    # No Chinese characters
    import re
    assert not re.search(r"[一-鿿]", sig)


def test_format_peer_signal_en_choose_uses_english_phrases():
    sig = format_peer_signal(_choose_report(), locale="en")
    assert "A" in sig
    assert "60" in sig
    import re
    assert not re.search(r"[一-鿿]", sig)


def test_per_focal_peer_signal_passes_locale_through():
    """When friend subset is empty, returns neutral text — but should be EN."""
    graph = FriendGraph()
    graph.add_edge("0", "1")
    # focal "0" with no peers in results yields neutral text path
    sig = per_focal_peer_signal(
        focal_idx=0, all_results=[], friend_graph=graph,
        persona_ids=["0", "1"], locale="en",
    )
    # neutral path should also avoid Chinese when locale="en"
    import re
    assert not re.search(r"[一-鿿]", sig)
