# engine/tests/test_debate_engine.py
import pytest
import json
from engine.analysts.debate import DebateEngine
from engine.analysts.base import AnalysisContext


MOCK_ANALYSIS_RESPONSE = json.dumps({
    "findings": ["发现测试数据"],
    "key_insights": ["测试洞察"],
    "narrative": "测试叙述",
})

MOCK_CHALLENGE_RESPONSE = json.dumps({
    "findings": ["挑战观点1"],
    "key_insights": ["替代解释1"],
    "narrative": "测试反面论证",
})

MOCK_SYNTHESIS_RESPONSE = json.dumps({
    "executive_summary": "测试执行摘要",
    "consensus": ["共识1"],
    "disagreements": [],
    "open_questions": ["问题1"],
    "timeline_narrative": [{"step": 1, "title": "开始", "description": "仿真启动", "significance": "high"}],
})


@pytest.mark.asyncio
async def test_debate_engine_full_run():
    call_count = 0

    async def mock_llm(prompt: str) -> str:
        nonlocal call_count
        call_count += 1
        if "综合" in prompt or "主持人" in prompt:
            return MOCK_SYNTHESIS_RESPONSE
        if "魔鬼代言人" in prompt or "挑战" in prompt:
            return MOCK_CHALLENGE_RESPONSE
        if "回应" in prompt or "辩论" in prompt:
            return "这是辩论回应内容"
        return MOCK_ANALYSIS_RESPONSE

    context = AnalysisContext(
        simulation_id="test_sim",
        platform="twitter",
        num_agents=10,
        num_steps=5,
        trace_data=[{"agent_id": i, "action": "create_post"} for i in range(20)],
        post_data=[{"content": f"test post {i}", "created_at_step": i % 5} for i in range(15)],
    )

    engine = DebateEngine(llm_call=mock_llm, debate_rounds=1)
    report = engine.run(context)
    result = await report

    assert result.executive_summary != ""
    assert "data_analyst" in result.analyst_reports
    assert "sociologist" in result.analyst_reports
    assert "psychologist" in result.analyst_reports
    assert "devils_advocate" in result.analyst_reports
    assert len(result.debate_log) > 0
    assert "posts_timeline" in result.chart_data


@pytest.mark.asyncio
async def test_debate_engine_progress_reporting():
    phases: list[tuple[str, float]] = []

    async def mock_llm(prompt: str) -> str:
        return MOCK_ANALYSIS_RESPONSE

    async def on_progress(phase: str, progress: float) -> None:
        phases.append((phase, progress))

    context = AnalysisContext(simulation_id="test", platform="twitter", num_agents=5, num_steps=3)
    engine = DebateEngine(llm_call=mock_llm, debate_rounds=1, on_progress=on_progress)
    await engine.run(context)

    phase_names = [p[0] for p in phases]
    assert "independent_analysis" in phase_names
    assert "debate" in phase_names
    assert "complete" in phase_names
