"""
Sistema centralizado de manejo de errores para APIs externas.
Proporciona logging estructurado, retry logic, y notificaciones de errores críticos.
"""

import asyncio
import logging
import traceback
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, field
from functools import wraps
import aiohttp
import httpx
try:
    from supabase.client import ClientError
except ImportError:
    # Fallback para versiones diferentes de supabase
    class ClientError(Exception):
        pass

# Configurar logger específico para errores de API
logger = logging.getLogger(__name__)


class APIErrorSeverity(Enum):
    """Niveles de severidad para errores de API."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class APIErrorType(Enum):
    """Tipos de errores de API."""
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    HTTP_ERROR = "http_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT = "rate_limit"
    SERVER_ERROR = "server_error"
    CLIENT_ERROR = "client_error"
    UNKNOWN_ERROR = "unknown_error"
    VALIDATION_ERROR = "validation_error"


@dataclass
class APIError:
    """Estructura para representar errores de API."""
    api_name: str
    error_type: APIErrorType
    severity: APIErrorSeverity
    message: str
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    request_url: Optional[str] = None
    request_method: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    max_retries: int = 3
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetryConfig:
    """Configuración para reintentos."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


class APIErrorHandler:
    """Manejador centralizado de errores para APIs externas."""
    
    def __init__(self):
        """Inicializa el manejador de errores."""
        self.error_history: List[APIError] = []
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self.default_retry_config = RetryConfig()
        
    def classify_error(
        self, 
        exception: Exception, 
        api_name: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None
    ) -> APIError:
        """
        Clasifica un error y determina su tipo y severidad.
        
        Args:
            exception: La excepción capturada
            api_name: Nombre de la API que falló
            status_code: Código de estado HTTP (si aplica)
            response_body: Cuerpo de la respuesta (si aplica)
            
        Returns:
            APIError clasificado
        """
        error_type = APIErrorType.UNKNOWN_ERROR
        severity = APIErrorSeverity.MEDIUM
        message = str(exception)
        
        # Clasificar por tipo de excepción
        if isinstance(exception, (aiohttp.ClientTimeout, httpx.TimeoutException, asyncio.TimeoutError)):
            error_type = APIErrorType.TIMEOUT
            severity = APIErrorSeverity.MEDIUM
            
        elif isinstance(exception, (aiohttp.ClientConnectionError, httpx.ConnectError, ConnectionError)):
            error_type = APIErrorType.CONNECTION_ERROR
            severity = APIErrorSeverity.HIGH
            
        elif isinstance(exception, (aiohttp.ClientResponseError, httpx.HTTPStatusError)):
            error_type = APIErrorType.HTTP_ERROR
            
            # Clasificar por código de estado
            if status_code:
                if status_code == 401:
                    error_type = APIErrorType.AUTHENTICATION_ERROR
                    severity = APIErrorSeverity.HIGH
                elif status_code == 429:
                    error_type = APIErrorType.RATE_LIMIT
                    severity = APIErrorSeverity.MEDIUM
                elif 400 <= status_code < 500:
                    error_type = APIErrorType.CLIENT_ERROR
                    severity = APIErrorSeverity.LOW
                elif 500 <= status_code < 600:
                    error_type = APIErrorType.SERVER_ERROR
                    severity = APIErrorSeverity.HIGH
                    
        elif isinstance(exception, ClientError):  # Supabase
            error_type = APIErrorType.SERVER_ERROR
            severity = APIErrorSeverity.HIGH
            
        elif isinstance(exception, ValueError):
            error_type = APIErrorType.VALIDATION_ERROR
            severity = APIErrorSeverity.LOW
            
        # APIs críticas tienen mayor severidad
        if api_name.lower() in ['supabase', 'database']:
            if severity == APIErrorSeverity.MEDIUM:
                severity = APIErrorSeverity.HIGH
            elif severity == APIErrorSeverity.HIGH:
                severity = APIErrorSeverity.CRITICAL
                
        return APIError(
            api_name=api_name,
            error_type=error_type,
            severity=severity,
            message=message,
            status_code=status_code,
            response_body=response_body[:500] if response_body else None  # Limitar tamaño
        )
    
    def should_retry(self, error: APIError) -> bool:
        """
        Determina si un error debe ser reintentado.
        
        Args:
            error: El error a evaluar
            
        Returns:
            True si debe reintentarse
        """
        # No reintentar errores de autenticación o validación
        if error.error_type in [APIErrorType.AUTHENTICATION_ERROR, APIErrorType.VALIDATION_ERROR]:
            return False
            
        # No reintentar errores de cliente (4xx excepto 429)
        if error.error_type == APIErrorType.CLIENT_ERROR and error.status_code != 429:
            return False
            
        # Verificar límite de reintentos
        if error.retry_count >= error.max_retries:
            return False
            
        # Verificar circuit breaker
        if self._is_circuit_breaker_open(error.api_name):
            return False
            
        return True
    
    def calculate_retry_delay(self, retry_count: int, config: RetryConfig) -> float:
        """
        Calcula el delay para el siguiente reintento.
        
        Args:
            retry_count: Número de reintentos realizados
            config: Configuración de reintentos
            
        Returns:
            Delay en segundos
        """
        delay = config.base_delay * (config.exponential_base ** retry_count)
        delay = min(delay, config.max_delay)
        
        if config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # Jitter del 50%
            
        return delay
    
    def log_error(self, error: APIError, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Registra un error en los logs con el nivel apropiado.
        
        Args:
            error: El error a registrar
            context: Contexto adicional
        """
        if context:
            error.context.update(context)
            
        # Agregar a historial
        self.error_history.append(error)
        
        # Mantener solo los últimos 1000 errores
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]
            
        # Log estructurado
        log_data = {
            "api_name": error.api_name,
            "error_type": error.error_type.value,
            "severity": error.severity.value,
            "error_message": error.message,  # Cambiar 'message' por 'error_message'
            "status_code": error.status_code,
            "retry_count": error.retry_count,
            "timestamp": error.timestamp.isoformat(),
            "context": error.context
        }
        
        # Seleccionar nivel de log
        if error.severity == APIErrorSeverity.CRITICAL:
            logger.critical(f"API Error - {error.api_name}: {error.message}", extra=log_data)
        elif error.severity == APIErrorSeverity.HIGH:
            logger.error(f"API Error - {error.api_name}: {error.message}", extra=log_data)
        elif error.severity == APIErrorSeverity.MEDIUM:
            logger.warning(f"API Error - {error.api_name}: {error.message}", extra=log_data)
        else:
            logger.info(f"API Error - {error.api_name}: {error.message}", extra=log_data)
            
        # Actualizar circuit breaker
        self._update_circuit_breaker(error.api_name, success=False)
    
    def log_success(self, api_name: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Registra una operación exitosa para resetear circuit breakers.
        
        Args:
            api_name: Nombre de la API
            context: Contexto adicional
        """
        self._update_circuit_breaker(api_name, success=True)
        
        if context:
            logger.debug(f"API Success - {api_name}", extra=context)
    
    def _is_circuit_breaker_open(self, api_name: str) -> bool:
        """Verifica si el circuit breaker está abierto para una API."""
        if api_name not in self.circuit_breakers:
            return False
            
        breaker = self.circuit_breakers[api_name]
        
        # Si está abierto, verificar si ya pasó el tiempo de cooldown
        if breaker["is_open"]:
            if datetime.now() > breaker["open_until"]:
                # Resetear circuit breaker
                breaker["is_open"] = False
                breaker["failure_count"] = 0
                logger.info(f"Circuit breaker reset for {api_name}")
                return False
            return True
            
        return False
    
    def _update_circuit_breaker(self, api_name: str, success: bool) -> None:
        """Actualiza el estado del circuit breaker."""
        if api_name not in self.circuit_breakers:
            self.circuit_breakers[api_name] = {
                "failure_count": 0,
                "is_open": False,
                "open_until": None,
                "last_failure": None
            }
            
        breaker = self.circuit_breakers[api_name]
        
        if success:
            breaker["failure_count"] = 0
        else:
            breaker["failure_count"] += 1
            breaker["last_failure"] = datetime.now()
            
            # Abrir circuit breaker después de 5 fallos consecutivos
            if breaker["failure_count"] >= 5:
                breaker["is_open"] = True
                breaker["open_until"] = datetime.now() + timedelta(minutes=5)
                logger.warning(f"Circuit breaker opened for {api_name} - too many failures")
    
    def get_error_stats(self, api_name: Optional[str] = None, hours: int = 24) -> Dict[str, Any]:
        """
        Obtiene estadísticas de errores.
        
        Args:
            api_name: Filtrar por API específica
            hours: Horas hacia atrás para analizar
            
        Returns:
            Estadísticas de errores
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Filtrar errores
        errors = [
            e for e in self.error_history 
            if e.timestamp > cutoff_time and (not api_name or e.api_name == api_name)
        ]
        
        if not errors:
            return {"total_errors": 0, "apis": {}, "error_types": {}, "severities": {}}
        
        # Agrupar por API
        apis = {}
        for error in errors:
            if error.api_name not in apis:
                apis[error.api_name] = 0
            apis[error.api_name] += 1
            
        # Agrupar por tipo
        error_types = {}
        for error in errors:
            error_type = error.error_type.value
            if error_type not in error_types:
                error_types[error_type] = 0
            error_types[error_type] += 1
            
        # Agrupar por severidad
        severities = {}
        for error in errors:
            severity = error.severity.value
            if severity not in severities:
                severities[severity] = 0
            severities[severity] += 1
        
        return {
            "total_errors": len(errors),
            "apis": apis,
            "error_types": error_types,
            "severities": severities,
            "circuit_breakers": {
                name: breaker for name, breaker in self.circuit_breakers.items()
                if breaker["failure_count"] > 0 or breaker["is_open"]
            }
        }


def with_error_handling(
    api_name: str,
    retry_config: Optional[RetryConfig] = None,
    context: Optional[Dict[str, Any]] = None
):
    """
    Decorador para agregar manejo de errores automático a funciones de API.
    
    Args:
        api_name: Nombre de la API
        retry_config: Configuración de reintentos
        context: Contexto adicional para logging
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            error_handler = get_error_handler()
            config = retry_config or error_handler.default_retry_config
            
            for attempt in range(config.max_retries + 1):
                try:
                    result = await func(*args, **kwargs)
                    error_handler.log_success(api_name, context)
                    return result
                    
                except Exception as e:
                    # Extraer información de la respuesta si está disponible
                    status_code = getattr(e, 'status_code', None) or getattr(e, 'response', {}).get('status_code')
                    response_body = None
                    
                    if hasattr(e, 'response') and e.response:
                        try:
                            response_body = str(e.response.text if hasattr(e.response, 'text') else e.response)
                        except:
                            pass
                    
                    error = error_handler.classify_error(e, api_name, status_code, response_body)
                    error.retry_count = attempt
                    error.max_retries = config.max_retries
                    
                    # Log del error
                    error_handler.log_error(error, context)
                    
                    # Verificar si debe reintentar
                    if attempt < config.max_retries and error_handler.should_retry(error):
                        delay = error_handler.calculate_retry_delay(attempt, config)
                        logger.info(f"Retrying {api_name} in {delay:.2f}s (attempt {attempt + 1}/{config.max_retries})")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # No más reintentos, re-lanzar la excepción
                        raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Para funciones síncronas, usar una versión simplificada
            error_handler = get_error_handler()
            
            try:
                result = func(*args, **kwargs)
                error_handler.log_success(api_name, context)
                return result
                
            except Exception as e:
                status_code = getattr(e, 'status_code', None)
                response_body = getattr(e, 'response', None)
                
                error = error_handler.classify_error(e, api_name, status_code, response_body)
                error_handler.log_error(error, context)
                raise
        
        # Detectar si la función es async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator


# Instancia global del manejador de errores
_error_handler: Optional[APIErrorHandler] = None


def get_error_handler() -> APIErrorHandler:
    """Obtiene la instancia global del manejador de errores."""
    global _error_handler
    if _error_handler is None:
        _error_handler = APIErrorHandler()
    return _error_handler


def reset_error_handler() -> None:
    """Resetea el manejador de errores (útil para tests)."""
    global _error_handler
    _error_handler = None 