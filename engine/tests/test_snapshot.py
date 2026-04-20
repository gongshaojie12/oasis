import os
import sqlite3
import tempfile

import pytest

from engine.timemachine.snapshot import RoundSnapshot, SnapshotExtractor


@pytest.fixture
def sim_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE user (
            user_id INTEGER PRIMARY KEY, agent_id INTEGER,
            user_name TEXT, name TEXT, bio TEXT, created_at TEXT,
            num_followings INTEGER DEFAULT 0, num_followers INTEGER DEFAULT 0
        );
        CREATE TABLE post (
            post_id INTEGER PRIMARY KEY, user_id INTEGER, content TEXT,
            created_at TEXT, num_likes INTEGER DEFAULT 0,
            num_dislikes INTEGER DEFAULT 0, num_shares INTEGER DEFAULT 0
        );
        CREATE TABLE trace (
            user_id INTEGER, created_at TEXT, action TEXT, info TEXT
        );

        INSERT INTO user VALUES (1, 1, 'alice', 'Alice', 'bio', '2026-01-01', 0, 0);
        INSERT INTO user VALUES (2, 2, 'bob', 'Bob', 'bio', '2026-01-01', 0, 0);

        INSERT INTO trace VALUES (1, '2026-01-01 00:01', 'CREATE_POST', '{}');
        INSERT INTO trace VALUES (2, '2026-01-01 00:02', 'LIKE_POST', '{}');
        INSERT INTO trace VALUES (1, '2026-01-01 00:03', 'CREATE_POST', '{}');
        INSERT INTO trace VALUES (2, '2026-01-01 00:04', 'FOLLOW', '{}');

        INSERT INTO post VALUES (1, 1, 'Hello', '2026-01-01 00:01', 0, 0, 0);
        INSERT INTO post VALUES (2, 1, 'World', '2026-01-01 00:03', 0, 0, 0);
    """)
    conn.close()
    yield path
    os.unlink(path)


def test_extract_round(sim_db):
    extractor = SnapshotExtractor(sim_db)
    snap = extractor.extract_round(1)
    assert isinstance(snap, RoundSnapshot)
    assert snap.round_number == 1
    assert snap.metrics["total_actions"] == 2


def test_extract_all(sim_db):
    extractor = SnapshotExtractor(sim_db)
    snaps = extractor.extract_all(2)
    assert len(snaps) == 2
    assert snaps[0].round_number == 1
    assert snaps[1].round_number == 2


def test_agent_summaries(sim_db):
    extractor = SnapshotExtractor(sim_db)
    snap = extractor.extract_round(1)
    assert len(snap.agent_summaries) > 0
    assert snap.agent_summaries[0].user_name in ("alice", "bob")


def test_empty_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE user (user_id INTEGER PRIMARY KEY, agent_id INTEGER, user_name TEXT, name TEXT, bio TEXT, created_at TEXT, num_followings INTEGER DEFAULT 0, num_followers INTEGER DEFAULT 0);
        CREATE TABLE post (post_id INTEGER PRIMARY KEY, user_id INTEGER, content TEXT, created_at TEXT, num_likes INTEGER DEFAULT 0, num_dislikes INTEGER DEFAULT 0, num_shares INTEGER DEFAULT 0);
        CREATE TABLE trace (user_id INTEGER, created_at TEXT, action TEXT, info TEXT);
    """)
    conn.close()
    extractor = SnapshotExtractor(path)
    snap = extractor.extract_round(1)
    assert snap.metrics["total_actions"] == 0
    os.unlink(path)
