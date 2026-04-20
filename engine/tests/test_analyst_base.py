# engine/tests/test_analyst_base.py
from engine.analysts.base import AnalysisContext, AnalystReport, DebateMessage, FinalReport


def test_analysis_context_defaults():
    ctx = AnalysisContext(
        simulation_id="sim_001",
        platform="twitter",
        num_agents=100,
        num_steps=10,
    )
    assert ctx.simulation_id == "sim_001"
    assert ctx.trace_data == []


def test_analyst_report_serialization():
    r = AnalystReport(
        analyst_role="data_analyst",
        perspective="quantitative",
        findings=["帖子数量呈上升趋势"],
        key_insights=["第5轮出现信息爆发"],
    )
    d = r.model_dump()
    assert d["analyst_role"] == "data_analyst"
    restored = AnalystReport.model_validate(d)
    assert restored.findings[0] == "帖子数量呈上升趋势"


def test_debate_message():
    msg = DebateMessage(
        round_num=1,
        speaker="sociologist",
        target="data_analyst",
        content="数据趋势并不能反映群体极化的深层原因",
        message_type="challenge",
    )
    assert msg.speaker == "sociologist"


def test_final_report_structure():
    r = FinalReport(
        executive_summary="仿真揭示了明显的群体极化趋势",
        consensus=["信息传播呈指数增长"],
        disagreements=[{"topic": "极化原因", "sides": {"sociologist": "结构性", "psychologist": "认知偏差"}}],
    )
    assert len(r.consensus) == 1
