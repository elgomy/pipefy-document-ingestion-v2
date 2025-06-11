"""
Servicio de notificaciones para errores críticos de APIs externas.
Envía alertas al equipo de operaciones cuando ocurren errores críticos.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from src.utils.error_handler import APIError, APIErrorSeverity, APIErrorType
from src.services.notification_service import NotificationService, NotificationRecipient, NotificationType

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Tipos de alertas para errores."""
    API_DOWN = "api_down"
    HIGH_ERROR_RATE = "high_error_rate"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    CRITICAL_ERROR = "critical_error"
    AUTHENTICATION_FAILURE = "authentication_failure"


@dataclass
class AlertConfig:
    """Configuración para alertas de errores."""
    enabled: bool = True
    error_rate_threshold: float = 0.1  # 10% de errores
    error_count_threshold: int = 10    # 10 errores en ventana de tiempo
    time_window_minutes: int = 15      # Ventana de tiempo para análisis
    cooldown_minutes: int = 30         # Tiempo entre alertas del mismo tipo
    critical_apis: List[str] = None    # APIs críticas que requieren alerta inmediata
    
    def __post_init__(self):
        if self.critical_apis is None:
            self.critical_apis = ["supabase", "database", "pipefy"]


class ErrorNotificationService:
    """Servicio para notificar errores críticos al equipo de operaciones."""
    
    def __init__(self, notification_service: Optional[NotificationService] = None):
        """
        Inicializa el servicio de notificaciones de errores.
        
        Args:
            notification_service: Servicio de notificaciones (opcional)
        """
        self.notification_service = notification_service
        self.config = AlertConfig()
        self.last_alerts: Dict[str, datetime] = {}  # Tracking de últimas alertas
        self.operations_team: List[NotificationRecipient] = []
        
        # Configurar equipo de operaciones por defecto
        self._setup_default_operations_team()
        
    def _setup_default_operations_team(self):
        """Configura el equipo de operaciones por defecto."""
        # En producción, estos datos vendrían de configuración/base de datos
        self.operations_team = [
            NotificationRecipient(
                name="Equipo de Operaciones",
                phone_number="+5511999999999",  # Número del equipo de ops
                role="operations_team",
                is_active=True
            )
        ]
    
    def add_operations_member(self, recipient: NotificationRecipient):
        """Agrega un miembro al equipo de operaciones."""
        self.operations_team.append(recipient)
    
    def remove_operations_member(self, phone_number: str):
        """Remueve un miembro del equipo de operaciones."""
        self.operations_team = [
            member for member in self.operations_team 
            if member.phone_number != phone_number
        ]
    
    async def process_error(self, error: APIError) -> bool:
        """
        Procesa un error y determina si debe enviar una alerta.
        
        Args:
            error: El error a procesar
            
        Returns:
            True si se envió una alerta
        """
        if not self.config.enabled:
            return False
            
        alert_sent = False
        
        # Verificar si es un error crítico
        if error.severity == APIErrorSeverity.CRITICAL:
            alert_sent = await self._send_critical_error_alert(error)
            
        # Verificar si es una API crítica con error de autenticación
        elif (error.api_name.lower() in self.config.critical_apis and 
              error.error_type == APIErrorType.AUTHENTICATION_ERROR):
            alert_sent = await self._send_authentication_failure_alert(error)
            
        # Verificar si es una API crítica que está caída
        elif (error.api_name.lower() in self.config.critical_apis and 
              error.error_type in [APIErrorType.CONNECTION_ERROR, APIErrorType.SERVER_ERROR]):
            alert_sent = await self._send_api_down_alert(error)
            
        return alert_sent
    
    async def check_error_rates(self, error_stats: Dict[str, Any]) -> bool:
        """
        Verifica las tasas de error y envía alertas si es necesario.
        
        Args:
            error_stats: Estadísticas de errores
            
        Returns:
            True si se envió alguna alerta
        """
        if not self.config.enabled:
            return False
            
        alert_sent = False
        
        # Verificar circuit breakers abiertos
        circuit_breakers = error_stats.get("circuit_breakers", {})
        for api_name, breaker_info in circuit_breakers.items():
            if breaker_info.get("is_open"):
                alert_sent = await self._send_circuit_breaker_alert(api_name, breaker_info) or alert_sent
        
        # Verificar tasas de error altas
        total_errors = error_stats.get("total_errors", 0)
        if total_errors >= self.config.error_count_threshold:
            alert_sent = await self._send_high_error_rate_alert(error_stats) or alert_sent
            
        return alert_sent
    
    async def _send_critical_error_alert(self, error: APIError) -> bool:
        """Envía alerta para error crítico."""
        alert_key = f"critical_{error.api_name}"
        
        if not self._should_send_alert(alert_key):
            return False
            
        message = self._format_critical_error_message(error)
        return await self._send_alert(AlertType.CRITICAL_ERROR, message, alert_key)
    
    async def _send_authentication_failure_alert(self, error: APIError) -> bool:
        """Envía alerta para fallo de autenticación."""
        alert_key = f"auth_{error.api_name}"
        
        if not self._should_send_alert(alert_key):
            return False
            
        message = self._format_authentication_failure_message(error)
        return await self._send_alert(AlertType.AUTHENTICATION_FAILURE, message, alert_key)
    
    async def _send_api_down_alert(self, error: APIError) -> bool:
        """Envía alerta para API caída."""
        alert_key = f"down_{error.api_name}"
        
        if not self._should_send_alert(alert_key):
            return False
            
        message = self._format_api_down_message(error)
        return await self._send_alert(AlertType.API_DOWN, message, alert_key)
    
    async def _send_circuit_breaker_alert(self, api_name: str, breaker_info: Dict[str, Any]) -> bool:
        """Envía alerta para circuit breaker abierto."""
        alert_key = f"circuit_{api_name}"
        
        if not self._should_send_alert(alert_key):
            return False
            
        message = self._format_circuit_breaker_message(api_name, breaker_info)
        return await self._send_alert(AlertType.CIRCUIT_BREAKER_OPEN, message, alert_key)
    
    async def _send_high_error_rate_alert(self, error_stats: Dict[str, Any]) -> bool:
        """Envía alerta para tasa de errores alta."""
        alert_key = "high_error_rate"
        
        if not self._should_send_alert(alert_key):
            return False
            
        message = self._format_high_error_rate_message(error_stats)
        return await self._send_alert(AlertType.HIGH_ERROR_RATE, message, alert_key)
    
    def _should_send_alert(self, alert_key: str) -> bool:
        """Verifica si debe enviar una alerta basado en cooldown."""
        now = datetime.now()
        last_alert = self.last_alerts.get(alert_key)
        
        if last_alert is None:
            return True
            
        cooldown = timedelta(minutes=self.config.cooldown_minutes)
        return now - last_alert > cooldown
    
    async def _send_alert(self, alert_type: AlertType, message: str, alert_key: str) -> bool:
        """
        Envía una alerta al equipo de operaciones.
        
        Args:
            alert_type: Tipo de alerta
            message: Mensaje de la alerta
            alert_key: Clave para tracking de cooldown
            
        Returns:
            True si se envió exitosamente
        """
        if not self.notification_service or not self.operations_team:
            logger.warning(f"Cannot send alert - notification service or operations team not configured")
            return False
            
        success_count = 0
        
        for recipient in self.operations_team:
            if not recipient.is_active:
                continue
                
            try:
                result = await self.notification_service.send_custom_notification(
                    recipient=recipient,
                    message=message,
                    notification_type=NotificationType.SYSTEM_ERROR
                )
                
                if result.success:
                    success_count += 1
                    logger.info(f"Alert sent to {recipient.name}: {alert_type.value}")
                else:
                    logger.error(f"Failed to send alert to {recipient.name}: {result.error_message}")
                    
            except Exception as e:
                logger.error(f"Error sending alert to {recipient.name}: {e}")
        
        # Marcar como enviada si al menos una notificación fue exitosa
        if success_count > 0:
            self.last_alerts[alert_key] = datetime.now()
            return True
            
        return False
    
    def _format_critical_error_message(self, error: APIError) -> str:
        """Formatea mensaje para error crítico."""
        return f"""🚨 ERROR CRÍTICO - {error.api_name.upper()}

⚠️ Severidad: CRÍTICA
🔧 Tipo: {error.error_type.value}
📝 Mensaje: {error.message}
🕐 Hora: {error.timestamp.strftime('%H:%M:%S')}

{f'📊 Status Code: {error.status_code}' if error.status_code else ''}

🔍 Requiere atención inmediata del equipo de operaciones."""
    
    def _format_authentication_failure_message(self, error: APIError) -> str:
        """Formatea mensaje para fallo de autenticación."""
        return f"""🔐 FALLO DE AUTENTICACIÓN - {error.api_name.upper()}

❌ Error de autenticación detectado
📝 Mensaje: {error.message}
🕐 Hora: {error.timestamp.strftime('%H:%M:%S')}

{f'📊 Status Code: {error.status_code}' if error.status_code else ''}

🔧 Verificar credenciales y configuración de API."""
    
    def _format_api_down_message(self, error: APIError) -> str:
        """Formatea mensaje para API caída."""
        return f"""📡 API CAÍDA - {error.api_name.upper()}

🔴 API no responde o error de servidor
🔧 Tipo: {error.error_type.value}
📝 Mensaje: {error.message}
🕐 Hora: {error.timestamp.strftime('%H:%M:%S')}

{f'📊 Status Code: {error.status_code}' if error.status_code else ''}

⚡ Verificar estado del servicio externo."""
    
    def _format_circuit_breaker_message(self, api_name: str, breaker_info: Dict[str, Any]) -> str:
        """Formatea mensaje para circuit breaker abierto."""
        failure_count = breaker_info.get("failure_count", 0)
        last_failure = breaker_info.get("last_failure")
        
        return f"""⚡ CIRCUIT BREAKER ABIERTO - {api_name.upper()}

🔴 Demasiados fallos consecutivos: {failure_count}
🕐 Último fallo: {last_failure.strftime('%H:%M:%S') if last_failure else 'N/A'}

🛡️ API temporalmente deshabilitada para prevenir cascada de errores.
🔧 Verificar estado del servicio y reiniciar si es necesario."""
    
    def _format_high_error_rate_message(self, error_stats: Dict[str, Any]) -> str:
        """Formatea mensaje para tasa de errores alta."""
        total_errors = error_stats.get("total_errors", 0)
        apis = error_stats.get("apis", {})
        
        top_apis = sorted(apis.items(), key=lambda x: x[1], reverse=True)[:3]
        
        message = f"""📈 TASA DE ERRORES ALTA

📊 Total errores (últimos {self.config.time_window_minutes}min): {total_errors}

🔝 APIs más afectadas:"""
        
        for api_name, count in top_apis:
            message += f"\n   • {api_name}: {count} errores"
            
        message += f"""

🔍 Revisar logs y estado de servicios externos."""
        
        return message
    
    def get_alert_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual de las alertas."""
        now = datetime.now()
        
        return {
            "config": {
                "enabled": self.config.enabled,
                "error_rate_threshold": self.config.error_rate_threshold,
                "error_count_threshold": self.config.error_count_threshold,
                "time_window_minutes": self.config.time_window_minutes,
                "cooldown_minutes": self.config.cooldown_minutes,
                "critical_apis": self.config.critical_apis
            },
            "operations_team": [
                {
                    "name": member.name,
                    "phone_number": member.phone_number,
                    "role": member.role,
                    "is_active": member.is_active
                }
                for member in self.operations_team
            ],
            "recent_alerts": [
                {
                    "alert_key": key,
                    "last_sent": timestamp.isoformat(),
                    "minutes_ago": int((now - timestamp).total_seconds() / 60)
                }
                for key, timestamp in self.last_alerts.items()
            ]
        }


# Instancia global del servicio
_error_notification_service: Optional[ErrorNotificationService] = None


def get_error_notification_service() -> ErrorNotificationService:
    """Obtiene la instancia global del servicio de notificaciones de errores."""
    global _error_notification_service
    if _error_notification_service is None:
        from src.services.notification_service import notification_service
        _error_notification_service = ErrorNotificationService(notification_service)
    return _error_notification_service 