"""SessionMemoryManager 集成测试 - JSONL 持久化恢复"""

import tempfile
from unittest.mock import MagicMock, patch

import pytest

from langchain_core.messages import HumanMessage, AIMessage


class TestSessionMemoryManagerPersistence:
    """测试 SessionMemoryManager 的 JSONL 持久化集成"""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """每个测试后重置单例，避免状态污染"""
        from app.memory import session_manager

        # 保存原始实例
        original_instance = session_manager.SessionMemoryManager._instance

        yield

        # 恢复
        session_manager.SessionMemoryManager._instance = original_instance

    @pytest.fixture
    def mock_persistence(self):
        """创建模拟的 SessionPersistenceManager"""
        mock = MagicMock()
        mock.list_sessions.return_value = {}
        return mock

    @pytest.fixture
    def manager_with_mock_persistence(self, mock_persistence):
        """创建带 mock persistence 的 SessionMemoryManager"""
        from app.memory import session_manager

        # 创建新实例（会触发单例）
        manager = session_manager.SessionMemoryManager()

        # 注入 mock persistence
        manager._persistence = mock_persistence
        manager._restored = False

        return manager

    def test_get_memory_loads_from_jsonl_when_session_exists(
        self, mock_persistence
    ):
        """测试 get_memory 时从 JSONL 加载已有会话"""
        session_id = "test_restore_session"

        # 模拟 persistence 返回的消息
        mock_persistence.list_sessions.return_value = {
            session_id: {
                "created_at": "2026-03-28T10:00:00Z",
                "updated_at": "2026-03-28T10:05:00Z",
                "message_count": 2,
            }
        }
        mock_persistence.load_session.return_value = [
            {"role": "human", "content": "你好，我想去东京"},
            {"role": "ai", "content": "好的，东京之旅，我来规划！"},
        ]

        from app.memory import session_manager

        # 重置单例以确保干净状态
        session_manager.SessionMemoryManager._instance = None

        with patch("app.memory.session_manager.get_session_persistence") as mock_get_persistence:
            mock_get_persistence.return_value = mock_persistence

            manager = session_manager.SessionMemoryManager()
            memory = manager.get_memory(session_id)

            # 验证消息已加载
            history = memory.get_history()
            assert len(history) == 2
            assert history[0].content == "你好，我想去东京"
            assert history[1].content == "好的，东京之旅，我来规划！"

    def test_restore_all_sessions_on_first_get_memory(self, mock_persistence):
        """测试首次调用 get_memory 时恢复所有会话"""
        session_ids = ["session_1", "session_2"]

        mock_persistence.list_sessions.return_value = {
            sid: {"created_at": "2026-03-28T10:00:00Z", "updated_at": "2026-03-28T10:05:00Z", "message_count": 1}
            for sid in session_ids
        }

        def mock_load(session_id):
            return [{"role": "human", "content": f"消息 from {session_id}"}]

        mock_persistence.load_session.side_effect = mock_load

        from app.memory import session_manager

        session_manager.SessionMemoryManager._instance = None

        with patch("app.memory.session_manager.get_session_persistence") as mock_get_persistence:
            mock_get_persistence.return_value = mock_persistence

            manager = session_manager.SessionMemoryManager()

            # 首次调用 - 触发恢复
            memory1 = manager.get_memory("session_1")

            # 验证所有会话都被恢复
            assert mock_persistence.list_sessions.call_count >= 1

            # 验证 session_2 也被恢复（即使没有直接调用 get_memory）
            assert "session_2" in manager._memories

    def test_does_not_restore_twice(self, mock_persistence):
        """测试恢复只执行一次（_restored 标志）"""
        session_id = "test_no_double_restore"

        mock_persistence.list_sessions.return_value = {
            session_id: {"created_at": "2026-03-28T10:00:00Z", "updated_at": "2026-03-28T10:05:00Z", "message_count": 1}
        }
        mock_persistence.load_session.return_value = [
            {"role": "human", "content": "测试消息"}
        ]

        from app.memory import session_manager

        session_manager.SessionMemoryManager._instance = None

        with patch("app.memory.session_manager.get_session_persistence") as mock_get_persistence:
            mock_get_persistence.return_value = mock_persistence

            manager = session_manager.SessionMemoryManager()

            # 多次调用 get_memory
            manager.get_memory(session_id)
            manager.get_memory("other_session")  # 另一个 session

            # list_sessions 只应被调用一次（首次 restore）
            assert mock_persistence.list_sessions.call_count == 1

    def test_get_memory_creates_new_when_not_in_jsonl(self, mock_persistence):
        """测试 get_memory 对不存在的会话创建新实例"""
        session_id = "brand_new_session"

        mock_persistence.list_sessions.return_value = {}  # 没有会话

        from app.memory import session_manager

        session_manager.SessionMemoryManager._instance = None

        with patch("app.memory.session_manager.get_session_persistence") as mock_get_persistence:
            mock_get_persistence.return_value = mock_persistence

            manager = session_manager.SessionMemoryManager()
            memory = manager.get_memory(session_id)

            # 验证返回的是新的空内存
            assert memory is not None
            assert len(memory.get_history()) == 0


class TestSessionMemoryManagerIntegration:
    """集成测试 - 使用真实的临时存储"""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """每个测试后重置单例"""
        from app.memory import session_manager

        original_instance = session_manager.SessionMemoryManager._instance

        yield

        session_manager.SessionMemoryManager._instance = original_instance

    @pytest.fixture
    def temp_persistence_dir(self):
        """创建临时目录用于持久化测试"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_full_flow_persistence_and_restore(self, temp_persistence_dir):
        """测试完整流程：保存消息 -> 重启 -> 恢复"""
        from app.memory.session_persistence import SessionPersistenceManager
        from app.memory import session_manager

        # 创建真实的 persistence manager
        persistence = SessionPersistenceManager(base_dir=temp_persistence_dir)

        # 保存一些消息
        session_id = "integration_test_session"
        persistence.save_message(
            session_id=session_id,
            role="human",
            content="你好，我想去东京旅行",
            user_id="user_001",
        )
        persistence.save_message(
            session_id=session_id,
            role="ai",
            content="好的，东京之旅，我来帮你规划！",
        )

        # 模拟重启：重置单例，注入新的 persistence
        session_manager.SessionMemoryManager._instance = None

        with patch("app.memory.session_manager.get_session_persistence") as mock_get_persistence:
            mock_get_persistence.return_value = persistence

            # 重启后首次获取 memory
            manager = session_manager.SessionMemoryManager()
            memory = manager.get_memory(session_id)

            # 验证消息已恢复
            history = memory.get_history()
            assert len(history) == 2
            assert history[0].content == "你好，我想去东京旅行"
            assert history[1].content == "好的，东京之旅，我来帮你规划！"
