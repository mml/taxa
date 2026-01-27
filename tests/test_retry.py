import pytest
import time
from unittest.mock import Mock, patch
from taxa.retry import with_retry, RateLimitError


def test_with_retry_succeeds_on_first_attempt():
    """Test that successful calls don't retry."""
    mock_func = Mock(return_value={"data": "success"})

    result = with_retry(mock_func, arg1="test")

    assert result == {"data": "success"}
    assert mock_func.call_count == 1


def test_with_retry_handles_network_errors():
    """Test exponential backoff for network errors."""
    mock_func = Mock(side_effect=[
        ConnectionError("Network error"),
        ConnectionError("Network error"),
        {"data": "success"}
    ])

    with patch('time.sleep') as mock_sleep:
        result = with_retry(mock_func)

    assert result == {"data": "success"}
    assert mock_func.call_count == 3
    # Should have slept with exponential backoff: 1s, 2s
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(1)
    mock_sleep.assert_any_call(2)


def test_with_retry_handles_429_rate_limit():
    """Test that 429 errors trigger exponential backoff."""
    error_429 = Exception("429 Client Error: Too Many Requests")

    mock_func = Mock(side_effect=[
        error_429,
        {"data": "success"}
    ])

    with patch('time.sleep') as mock_sleep:
        result = with_retry(mock_func)

    assert result == {"data": "success"}
    assert mock_func.call_count == 2
    mock_sleep.assert_called_once_with(1)


def test_with_retry_gives_up_after_max_attempts():
    """Test that retry gives up after max attempts."""
    mock_func = Mock(side_effect=ConnectionError("Network error"))

    with patch('time.sleep'):
        with pytest.raises(ConnectionError):
            with_retry(mock_func, max_attempts=3)

    assert mock_func.call_count == 3


def test_with_retry_handles_timeout_errors():
    """Test that timeout errors are retried."""
    mock_func = Mock(side_effect=[
        TimeoutError("Request timeout"),
        {"data": "success"}
    ])

    with patch('time.sleep') as mock_sleep:
        result = with_retry(mock_func)

    assert result == {"data": "success"}
    assert mock_func.call_count == 2
