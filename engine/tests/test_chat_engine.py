import os
import sqlite3
import tempfile

import pytest

from engine.timemachine.chat import AgentChatEngine, ChatMessage, ChatResponse


@pytest.fixture
def chat_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE user (
            user_id INTEGER PRIMARY KEY, agent_id INTEGER,
            user_name TEXT, name TEXT, bio TEXT, created_at TEXT,
            num_followings INTEGER DEFAULT 0, num_followers INTEGER DEFAULT 0
        );
        CREATE TABLE trace (
            user_id INTEGER, created_at TEXT, action TEXT, info TEXT
        );

        INSERT INTO user VALUES (1, 1, 'alice', 'Alice', 'Tech enthusiast', '2026-01-01', 5, 10);
        INSERT INTO user VALUES (2, 2, 'bob', 'Bob', 'Sports fan', '2026-01-01', 3, 8);

        INSERT INTO trace VALUES (1, '2026-01-01 00:01', 'CREATE_POST', '{}');
        INSERT INTO trace VALUES (2, '2026-01-01 00:02', 'LIKE_POST', '{}');
        INSERT INTO trace VALUES (1, '2026-01-01 00:03', 'FOLLOW', '{}');
        INSERT INTO trace VALUES (2, '2026-01-01 00:04', 'CREATE_POST', '{}');
    """)
    conn.close()
    yield path
    os.unlink(path)


@pytest.mark.asyncio
async def test_chat_basic(chat_db):
    async def mock_llm(prompt: str) -> str:
        return "I think technology is evolving rapidly."

    engine = AgentChatEngine(db_path=chat_db, llm_call=mock_llm)
    result = await engine.chat(agent_id=1, round_context=1, user_message="What do you think?")

    assert isinstance(result, ChatResponse)
    assert result.agent_id == 1
    assert result.agent_name == "alice"
    assert result.context_round == 1
    assert "technology" in result.response


@pytest.mark.asyncio
async def test_roundtable(chat_db):
    call_count = 0

    async def mock_llm(prompt: str) -> str:
        nonlocal call_count
        call_count += 1
        return f"Response {call_count}"

    engine = AgentChatEngine(db_path=chat_db, llm_call=mock_llm)
    messages = await engine.roundtable(
        agent_ids=[1, 2], round_context=1, topic="Tech trends", num_rounds=2,
    )

    assert len(messages) == 4
    assert messages[0].agent_id == 1
    assert messages[1].agent_id == 2
    assert all(m.role == "agent" for m in messages)
