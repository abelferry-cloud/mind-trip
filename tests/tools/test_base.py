import pytest
from app.tools.base import ToolErrorCategory, ToolException, ToolResult


class TestToolErrorCategory:
    def test_error_categories_exist(self):
        assert ToolErrorCategory.API_ERROR.value == "API_ERROR"
        assert ToolErrorCategory.VALIDATION_ERROR.value == "VALIDATION_ERROR"
        assert ToolErrorCategory.NETWORK_ERROR.value == "NETWORK_ERROR"
        assert ToolErrorCategory.TIMEOUT_ERROR.value == "TIMEOUT_ERROR"
        assert ToolErrorCategory.UNKNOWN_ERROR.value == "UNKNOWN_ERROR"


class TestToolException:
    def test_exception_creation(self):
        exc = ToolException(
            category=ToolErrorCategory.API_ERROR,
            message="API failed",
            details={"status_code": 500},
            retryable=True
        )
        assert exc.category == ToolErrorCategory.API_ERROR
        assert exc.message == "API failed"
        assert exc.details == {"status_code": 500}
        assert exc.retryable is True

    def test_exception_defaults(self):
        exc = ToolException(category=ToolErrorCategory.UNKNOWN_ERROR, message="Unknown")
        assert exc.details == {}
        assert exc.retryable is False

    def test_exception_isinstance(self):
        exc = ToolException(category=ToolErrorCategory.NETWORK_ERROR, message="Network error")
        assert isinstance(exc, Exception)


class TestToolResult:
    def test_result_success(self):
        result = ToolResult(success=True, data={"key": "value"})
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.metadata == {}

    def test_result_failure(self):
        exc = ToolException(category=ToolErrorCategory.API_ERROR, message="Failed")
        result = ToolResult(success=False, error=exc, metadata={"retry_count": 2})
        assert result.success is False
        assert result.error == exc
        assert result.metadata["retry_count"] == 2

    def test_result_metadata_defaults(self):
        result = ToolResult(success=True)
        assert result.metadata == {}
