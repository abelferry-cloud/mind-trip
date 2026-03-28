"""会话持久化端到端测试。"""

import tempfile
from pathlib import Path

import pytest

from app.memory.session_manager import SessionMemoryManager
from app.memory.session_persistence import SessionPersistenceManager


class TestFullLifecycle:
    """测试创建 → 发送消息 → 重启 → 恢复。"""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """每个测试后重置单例，避免状态污染。"""
        from app.memory import session_manager

        original_instance = session_manager.SessionMemoryManager._instance
        yield
        session_manager.SessionMemoryManager._instance = original_instance

    def test_full_lifecycle(self):
        """测试创建会话、写入消息、模拟重启、从 JSONL 恢复。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 第一次：创建会话，写入消息
            persistence = SessionPersistenceManager(base_dir=tmpdir)

            # 重置单例并注入 persistence
            from app.memory import session_manager
            session_manager.SessionMemoryManager._instance = None
            manager1 = session_manager.SessionMemoryManager()
            manager1._persistence = persistence
            manager1._restored = False

            sid = "test-lifecycle"
            mem1 = manager1.get_memory(sid)
            mem1.save_context({"input": "你好"}, {"output": "你好！"})
            # 模拟 ChatService 的持久化行为：save_context 后调用 persistence
            persistence.save_message(sid, "human", "你好", user_id=None)
            persistence.save_message(sid, "ai", "你好！")

            # 验证已写入 JSONL
            jsonl_file = Path(tmpdir) / f"{sid}.jsonl"
            assert jsonl_file.exists()

            # 验证 sessions.json
            index = persistence.list_sessions()
            assert sid in index
            assert index[sid]["message_count"] == 2

            # 第二次：模拟重启，新实例从 JSONL 恢复
            session_manager.SessionMemoryManager._instance = None
            manager2 = session_manager.SessionMemoryManager()
            manager2._persistence = persistence
            manager2._restored = False

            mem2 = manager2.get_memory(sid)
            history = mem2.get_history()
            assert len(history) == 2
            assert "你好" in history[0].content
            assert "你好！" in history[1].content


class TestDeleteSession:
    """测试删除会话后 JSONL 文件被删除。"""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """每个测试后重置单例。"""
        from app.memory import session_manager

        original_instance = session_manager.SessionMemoryManager._instance
        yield
        session_manager.SessionMemoryManager._instance = original_instance

    def test_delete_session_removes_jsonl(self):
        """测试删除会话后 JSONL 文件被删除。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = SessionPersistenceManager(base_dir=tmpdir)

            from app.memory import session_manager
            session_manager.SessionMemoryManager._instance = None
            manager = session_manager.SessionMemoryManager()
            manager._persistence = persistence
            manager._restored = False

            sid = "test-delete"
            mem = manager.get_memory(sid)
            mem.save_context({"input": "test"}, {"output": "result"})
            # 模拟 ChatService 的持久化行为
            persistence.save_message(sid, "human", "test", user_id=None)
            persistence.save_message(sid, "ai", "result")

            jsonl_file = Path(tmpdir) / f"{sid}.jsonl"
            assert jsonl_file.exists()

            # 删除会话
            persistence.delete_session(sid)
            manager.clear_session(sid)

            # JSONL 文件应不存在
            assert not jsonl_file.exists()


class TestMultipleSessions:
    """测试多个会话隔离存储。"""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """每个测试后重置单例。"""
        from app.memory import session_manager

        original_instance = session_manager.SessionMemoryManager._instance
        yield
        session_manager.SessionMemoryManager._instance = original_instance

    def test_multiple_sessions(self):
        """测试多个会话隔离存储。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = SessionPersistenceManager(base_dir=tmpdir)

            sid1 = "session-1"
            sid2 = "session-2"

            # 写入两个会话
            persistence.save_message(sid1, "human", "msg1", user_id="u1")
            persistence.save_message(sid2, "human", "msg2", user_id="u2")

            # 分别读取验证
            msgs1 = persistence.load_session(sid1)
            msgs2 = persistence.load_session(sid2)

            assert len(msgs1) == 1
            assert msgs1[0]["content"] == "msg1"
            assert len(msgs2) == 1
            assert msgs2[0]["content"] == "msg2"

    def test_multiple_sessions_with_manager(self):
        """测试通过 SessionMemoryManager 访问多个会话的隔离性。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = SessionPersistenceManager(base_dir=tmpdir)

            from app.memory import session_manager
            session_manager.SessionMemoryManager._instance = None
            manager = session_manager.SessionMemoryManager()
            manager._persistence = persistence
            manager._restored = False

            sid1 = "multi-session-1"
            sid2 = "multi-session-2"

            # 分别为两个会话写入消息
            mem1 = manager.get_memory(sid1)
            mem1.save_context({"input": "first"}, {"output": "response1"})

            mem2 = manager.get_memory(sid2)
            mem2.save_context({"input": "second"}, {"output": "response2"})

            # 验证两个会话的消息历史互相独立
            history1 = mem1.get_history()
            history2 = mem2.get_history()

            assert len(history1) == 2
            assert len(history2) == 2
            assert "first" in history1[0].content
            assert "response1" in history1[1].content
            assert "second" in history2[0].content
            assert "response2" in history2[1].content
