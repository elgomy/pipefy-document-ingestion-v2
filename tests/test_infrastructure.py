"""
Test básico para verificar que la infraestructura de testing funciona correctamente.
"""
import pytest
import asyncio
from unittest.mock import MagicMock


@pytest.mark.unit
def test_pytest_working():
    """Test básico para verificar que pytest funciona."""
    assert True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_support():
    """Test para verificar que el soporte async funciona."""
    await asyncio.sleep(0.001)
    assert True


@pytest.mark.unit
def test_mock_support():
    """Test para verificar que el mock funciona."""
    mock = MagicMock()
    mock.test_method.return_value = "test_value"
    
    result = mock.test_method()
    assert result == "test_value"
    mock.test_method.assert_called_once()
