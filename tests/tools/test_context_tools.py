import pytest
from app.tools.context_tools import UpdateUserContextInput


class TestUpdateUserContextInput:
    def test_valid_input(self):
        data = UpdateUserContextInput(
            user_name="张三",
            preferred_name="小张",
            identity="软件工程师",
            language="中文",
            timezone="Asia/Shanghai"
        )
        assert data.user_name == "张三"
        assert data.preferred_name == "小张"

    def test_user_name_required(self):
        with pytest.raises(Exception):
            UpdateUserContextInput(user_name="")

    def test_user_name_too_long(self):
        with pytest.raises(Exception):
            UpdateUserContextInput(user_name="x" * 51)

    def test_default_values(self):
        data = UpdateUserContextInput(user_name="张三")
        assert data.preferred_name == ""
        assert data.identity == ""
        assert data.language == "中文"
        assert data.timezone == "Asia/Shanghai"
        assert data.notes == ""
