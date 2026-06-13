# =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
from wanxiang.actions.l1_decision import L1_ACTIONS
from wanxiang.actions.layers import ActionLayer


def test_l1_has_core_decision_actions():
    names = {a.name for a in L1_ACTIONS}
    assert {"rate", "choose", "click_probability", "sentiment", "willingness_to_pay"} <= names


def test_l1_actions_all_in_l1_layer():
    assert all(a.layer is ActionLayer.L1_DECISION for a in L1_ACTIONS)


def test_l1_rate_has_score_param():
    rate = next(a for a in L1_ACTIONS if a.name == "rate")
    assert "score" in rate.params


def test_l1_choose_has_option_param():
    choose = next(a for a in L1_ACTIONS if a.name == "choose")
    assert "option" in choose.params


def test_l1_action_names_unique():
    names = [a.name for a in L1_ACTIONS]
    assert len(names) == len(set(names))
