"""
Pruebas unitarias simplificadas para el sistema de manejo de errores.
"""

import pytest
import asyncio
import logging
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from src.utils.error_handler import (
    APIErrorHandler,
    APIError,
    APIErrorType,
    APIErrorSeverity,
    RetryConfig,
    with_error_handling
)

class TestAPIErrorHandler:
    """Pruebas para APIErrorHandler."""
    
    @pytest.fixture
    def error_handler(self):
        """Fixture del error handler."""
        return APIErrorHandler()
    
    def test_init(self, error_handler):
        """Prueba la inicialización del error handler."""
        assert error_handler is not None
        assert error_handler.error_history == []
        assert error_handler.circuit_breakers == {}
        assert error_handler.default_retry_config.max_retries == 3
    
    def test_classify_error_timeout(self, error_handler):
        """Prueba clasificación de error de timeout."""
        timeout_error = asyncio.TimeoutError("Request timeout")
        
        api_error = error_handler.classify_error(timeout_error, "TestAPI")
        
        assert api_error.error_type == APIErrorType.TIMEOUT
        assert api_error.severity == APIErrorSeverity.MEDIUM
        assert api_error.api_name == "TestAPI"
    
    def test_classify_error_connection(self, error_handler):
        """Prueba clasificación de error de conexión."""
        connection_error = ConnectionError("Connection failed")
        
        api_error = error_handler.classify_error(connection_error, "TestAPI")
        
        assert api_error.error_type == APIErrorType.CONNECTION_ERROR
        assert api_error.severity == APIErrorSeverity.HIGH
    
    def test_classify_error_authentication(self, error_handler):
        """Prueba clasificación de error de autenticación."""
        import aiohttp
        from unittest.mock import Mock
        
        # Crear un mock de request info
        mock_request_info = Mock()
        mock_request_info.real_url = "http://test.com"
        
        # Crear ClientResponseError con mock apropiado
        auth_error = aiohttp.ClientResponseError(mock_request_info, (), status=401, message="Unauthorized")
        
        api_error = error_handler.classify_error(auth_error, "TestAPI", status_code=401)
        
        assert api_error.error_type == APIErrorType.AUTHENTICATION_ERROR
        assert api_error.severity == APIErrorSeverity.HIGH
    
    def test_classify_error_rate_limit(self, error_handler):
        """Prueba clasificación de error de rate limit."""
        import aiohttp
        from unittest.mock import Mock
        
        # Crear un mock de request info
        mock_request_info = Mock()
        mock_request_info.real_url = "http://test.com"
        
        # Crear ClientResponseError con mock apropiado
        rate_limit_error = aiohttp.ClientResponseError(mock_request_info, (), status=429, message="Too Many Requests")
        
        api_error = error_handler.classify_error(rate_limit_error, "TestAPI", status_code=429)
        
        assert api_error.error_type == APIErrorType.RATE_LIMIT
        assert api_error.severity == APIErrorSeverity.MEDIUM
    
    def test_classify_error_server_error(self, error_handler):
        """Prueba clasificación de error de servidor."""
        import aiohttp
        from unittest.mock import Mock
        
        # Crear un mock de request info
        mock_request_info = Mock()
        mock_request_info.real_url = "http://test.com"
        
        # Crear ClientResponseError con mock apropiado
        server_error = aiohttp.ClientResponseError(mock_request_info, (), status=500, message="Internal Server Error")
        
        api_error = error_handler.classify_error(server_error, "TestAPI", status_code=500)
        
        assert api_error.error_type == APIErrorType.SERVER_ERROR
        assert api_error.severity == APIErrorSeverity.HIGH
    
    def test_classify_error_validation(self, error_handler):
        """Prueba clasificación de error de validación."""
        validation_error = ValueError("Invalid input")
        
        api_error = error_handler.classify_error(validation_error, "TestAPI")
        
        assert api_error.error_type == APIErrorType.VALIDATION_ERROR
        assert api_error.severity == APIErrorSeverity.LOW
    
    def test_classify_error_unknown(self, error_handler):
        """Prueba clasificación de error desconocido."""
        unknown_error = Exception("Unknown error")
        
        api_error = error_handler.classify_error(unknown_error, "TestAPI")
        
        assert api_error.error_type == APIErrorType.UNKNOWN_ERROR
        assert api_error.severity == APIErrorSeverity.MEDIUM
    
    def test_should_retry_timeout(self, error_handler):
        """Prueba si debe reintentar en caso de timeout."""
        api_error = APIError(
            api_name="TestAPI",
            error_type=APIErrorType.TIMEOUT,
            severity=APIErrorSeverity.MEDIUM,
            message="Timeout",
            retry_count=1,
            max_retries=3
        )
        
        assert error_handler.should_retry(api_error) is True
    
    def test_should_retry_max_attempts(self, error_handler):
        """Prueba que no reintente si se alcanzó el máximo de intentos."""
        api_error = APIError(
            api_name="TestAPI",
            error_type=APIErrorType.TIMEOUT,
            severity=APIErrorSeverity.MEDIUM,
            message="Timeout",
            retry_count=3,
            max_retries=3
        )
        
        assert error_handler.should_retry(api_error) is False
    
    def test_should_retry_authentication_error(self, error_handler):
        """Prueba que no reintente en caso de error de autenticación."""
        api_error = APIError(
            api_name="TestAPI",
            error_type=APIErrorType.AUTHENTICATION_ERROR,
            severity=APIErrorSeverity.HIGH,
            message="Unauthorized",
            retry_count=1,
            max_retries=3
        )
        
        assert error_handler.should_retry(api_error) is False
    
    def test_should_retry_validation_error(self, error_handler):
        """Prueba que no reintente en caso de error de validación."""
        api_error = APIError(
            api_name="TestAPI",
            error_type=APIErrorType.VALIDATION_ERROR,
            severity=APIErrorSeverity.LOW,
            message="Invalid input",
            retry_count=1,
            max_retries=3
        )
        
        assert error_handler.should_retry(api_error) is False
    
    def test_should_retry_circuit_breaker_open(self, error_handler):
        """Prueba que no reintente si el circuit breaker está abierto."""
        # Simula circuit breaker abierto
        error_handler.circuit_breakers["TestAPI"] = {
            "failure_count": 6,
            "is_open": True,
            "open_until": datetime.now() + timedelta(minutes=5),
            "last_failure": datetime.now()
        }
        
        api_error = APIError(
            api_name="TestAPI",
            error_type=APIErrorType.TIMEOUT,
            severity=APIErrorSeverity.MEDIUM,
            message="Timeout",
            retry_count=1,
            max_retries=3
        )
        
        assert error_handler.should_retry(api_error) is False
    
    def test_log_error(self, error_handler, caplog):
        """Prueba el logging de errores."""
        with caplog.at_level(logging.WARNING):
            api_error = APIError(
                api_name="TestAPI",
                error_type=APIErrorType.TIMEOUT,
                severity=APIErrorSeverity.MEDIUM,
                message="Test timeout"
            )
            
            error_handler.log_error(api_error)
            
            assert "API Error" in caplog.text
            assert "TestAPI" in caplog.text
    
    def test_log_error_updates_history(self, error_handler):
        """Prueba que el logging actualiza el historial."""
        api_error = APIError(
            api_name="TestAPI",
            error_type=APIErrorType.TIMEOUT,
            severity=APIErrorSeverity.MEDIUM,
            message="Test timeout"
        )
        
        error_handler.log_error(api_error)
        
        assert len(error_handler.error_history) == 1
        assert error_handler.error_history[0] == api_error
    
    def test_get_error_stats_empty(self, error_handler):
        """Prueba estadísticas vacías."""
        stats = error_handler.get_error_stats()
        
        assert stats["total_errors"] == 0
        assert stats["apis"] == {}
        assert stats["error_types"] == {}
    
    def test_calculate_retry_delay(self, error_handler):
        """Prueba cálculo de delay de reintento."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, max_delay=10.0, jitter=False)
        
        # Primer reintento (sin jitter)
        delay1 = error_handler.calculate_retry_delay(0, config)
        assert delay1 == 1.0
        
        # Segundo reintento (sin jitter)
        delay2 = error_handler.calculate_retry_delay(1, config)
        assert delay2 == 2.0
        
        # Verificar límite máximo
        delay_max = error_handler.calculate_retry_delay(10, config)
        assert delay_max <= 10.0
    
    def test_retry_config_dataclass(self):
        """Prueba el dataclass RetryConfig."""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=30.0,
            exponential_base=1.5,
            jitter=False
        )
        
        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 1.5
        assert config.jitter is False
    
    def test_api_error_dataclass(self):
        """Prueba el dataclass APIError."""
        error = APIError(
            api_name="TestAPI",
            error_type=APIErrorType.TIMEOUT,
            severity=APIErrorSeverity.HIGH,
            message="Test error",
            status_code=408,
            retry_count=2,
            max_retries=3
        )
        
        assert error.api_name == "TestAPI"
        assert error.error_type == APIErrorType.TIMEOUT
        assert error.severity == APIErrorSeverity.HIGH
        assert error.message == "Test error"
        assert error.status_code == 408
        assert error.retry_count == 2
        assert error.max_retries == 3


class TestWithErrorHandlingDecorator:
    """Pruebas para el decorador with_error_handling."""
    
    @pytest.mark.asyncio
    async def test_decorator_success(self):
        """Prueba decorador con función exitosa."""
        @with_error_handling("TestAPI")
        async def test_func():
            return "success"
        
        result = await test_func()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_decorator_with_retries(self):
        """Prueba decorador con reintentos."""
        call_count = 0
        
        @with_error_handling("TestAPI", retry_config=RetryConfig(max_retries=3, base_delay=0.01))
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise asyncio.TimeoutError("Timeout")
            return "success"
        
        result = await test_func()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_decorator_max_retries_exceeded(self):
        """Prueba decorador cuando se exceden los reintentos."""
        @with_error_handling("TestAPI", retry_config=RetryConfig(max_retries=1, base_delay=0.01))
        async def test_func():
            raise asyncio.TimeoutError("Persistent timeout")
        
        with pytest.raises(asyncio.TimeoutError):
            await test_func()
    
    @pytest.mark.asyncio
    async def test_decorator_no_retry_on_auth_error(self):
        """Prueba que no reintente en errores de autenticación."""
        call_count = 0
        
        @with_error_handling("TestAPI")
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Authentication failed")
        
        with pytest.raises(ValueError):
            await test_func()
        
        assert call_count == 1  # No debería reintentar
    
    @pytest.mark.asyncio
    async def test_decorator_with_custom_config(self):
        """Prueba decorador con configuración personalizada."""
        config = RetryConfig(max_retries=2, base_delay=0.1)
        
        @with_error_handling("TestAPI", retry_config=config)
        async def test_func():
            return "success"
        
        result = await test_func()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_decorator_preserves_function_metadata(self):
        """Prueba que el decorador preserva metadatos de función."""
        @with_error_handling("TestAPI")
        async def test_func():
            """Test function docstring."""
            return "success"
        
        assert test_func.__name__ == "test_func"
        assert "Test function docstring" in test_func.__doc__
    
    @pytest.mark.asyncio
    async def test_decorator_with_args_and_kwargs(self):
        """Prueba decorador con argumentos y kwargs."""
        @with_error_handling("TestAPI")
        async def test_func(arg1, arg2, kwarg1=None):
            return f"{arg1}-{arg2}-{kwarg1}"
        
        result = await test_func("a", "b", kwarg1="c")
        assert result == "a-b-c" 