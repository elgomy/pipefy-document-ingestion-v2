"""
Sistema centralizado de métricas e monitoreo.
Coleta e agrega métricas de todos os serviços externos.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class ServiceType(Enum):
    """Tipos de serviços monitorados."""
    PIPEFY = "pipefy"
    CREWAI = "crewai"
    TWILIO = "twilio"
    CNPJ = "cnpj"
    SUPABASE = "supabase"

class AlertLevel(Enum):
    """Níveis de alerta."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ServiceMetrics:
    """Métricas de um serviço específico."""
    service_type: ServiceType
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timeout_requests: int = 0
    avg_response_time: float = 0.0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    circuit_breaker_open: bool = False
    response_times: List[float] = field(default_factory=list)
    
    def success_rate(self) -> float:
        """Calcula taxa de sucesso."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    def update_response_time(self, response_time: float):
        """Atualiza tempo de resposta."""
        self.response_times.append(response_time)
        
        # Manter apenas os últimos 100 tempos
        if len(self.response_times) > 100:
            self.response_times = self.response_times[-100:]
        
        # Recalcular média
        if self.response_times:
            self.avg_response_time = sum(self.response_times) / len(self.response_times)

@dataclass
class Alert:
    """Representa um alerta do sistema."""
    timestamp: datetime
    service_type: ServiceType
    level: AlertLevel
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "service": self.service_type.value,
            "level": self.level.value,
            "message": self.message,
            "context": self.context
        }

class MetricsService:
    """Serviço centralizado de métricas e monitoreo."""
    
    def __init__(self):
        self.metrics: Dict[ServiceType, ServiceMetrics] = {}
        self.alerts: List[Alert] = []
        self.alert_thresholds = {
            "failure_rate": 20.0,  # % de falhas que gera alerta
            "consecutive_failures": 3,  # Falhas consecutivas para alerta
            "response_time": 30.0,  # Tempo de resposta em segundos para alerta
            "timeout_rate": 10.0  # % de timeouts que gera alerta
        }
        
        # Inicializar métricas para todos os serviços
        for service_type in ServiceType:
            self.metrics[service_type] = ServiceMetrics(service_type=service_type)
    
    def record_request(self, service_type: ServiceType, success: bool, 
                      response_time: float, is_timeout: bool = False,
                      error_message: Optional[str] = None):
        """Registra uma requisição."""
        metrics = self.metrics[service_type]
        
        metrics.total_requests += 1
        
        if success:
            metrics.successful_requests += 1
            metrics.last_success = datetime.now()
            metrics.consecutive_failures = 0
            metrics.circuit_breaker_open = False
        else:
            metrics.failed_requests += 1
            metrics.last_failure = datetime.now()
            metrics.consecutive_failures += 1
            
            # Verificar se deve abrir circuit breaker
            if metrics.consecutive_failures >= self.alert_thresholds["consecutive_failures"]:
                metrics.circuit_breaker_open = True
        
        if is_timeout:
            metrics.timeout_requests += 1
        
        metrics.update_response_time(response_time)
        
        # Verificar condições de alerta
        self._check_alerts(service_type, error_message)
    
    def _check_alerts(self, service_type: ServiceType, error_message: Optional[str] = None):
        """Verifica condições que geram alertas."""
        metrics = self.metrics[service_type]
        
        # Alerta por taxa de falhas alta
        if metrics.total_requests >= 10:  # Só alertar após ter dados suficientes
            failure_rate = (metrics.failed_requests / metrics.total_requests) * 100
            if failure_rate >= self.alert_thresholds["failure_rate"]:
                self._create_alert(
                    service_type, 
                    AlertLevel.WARNING,
                    f"Alta taxa de falhas: {failure_rate:.1f}%",
                    {"failure_rate": failure_rate, "total_requests": metrics.total_requests}
                )
        
        # Alerta por falhas consecutivas
        if metrics.consecutive_failures >= self.alert_thresholds["consecutive_failures"]:
            self._create_alert(
                service_type,
                AlertLevel.ERROR,
                f"Falhas consecutivas: {metrics.consecutive_failures}",
                {"consecutive_failures": metrics.consecutive_failures, "error": error_message}
            )
        
        # Alerta por tempo de resposta alto
        if metrics.avg_response_time >= self.alert_thresholds["response_time"]:
            self._create_alert(
                service_type,
                AlertLevel.WARNING,
                f"Tempo de resposta alto: {metrics.avg_response_time:.2f}s",
                {"avg_response_time": metrics.avg_response_time}
            )
        
        # Alerta por taxa de timeout alta
        if metrics.total_requests >= 5:
            timeout_rate = (metrics.timeout_requests / metrics.total_requests) * 100
            if timeout_rate >= self.alert_thresholds["timeout_rate"]:
                self._create_alert(
                    service_type,
                    AlertLevel.WARNING,
                    f"Alta taxa de timeouts: {timeout_rate:.1f}%",
                    {"timeout_rate": timeout_rate, "timeout_requests": metrics.timeout_requests}
                )
    
    def _create_alert(self, service_type: ServiceType, level: AlertLevel, 
                     message: str, context: Dict[str, Any]):
        """Cria um novo alerta."""
        alert = Alert(
            timestamp=datetime.now(),
            service_type=service_type,
            level=level,
            message=message,
            context=context
        )
        
        self.alerts.append(alert)
        
        # Manter apenas os últimos 1000 alertas
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]
        
        # Log do alerta
        log_level = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.ERROR: logging.ERROR,
            AlertLevel.CRITICAL: logging.CRITICAL
        }[level]
        
        logger.log(log_level, f"🚨 ALERTA [{service_type.value.upper()}] {message}")
    
    def get_service_metrics(self, service_type: ServiceType) -> Dict[str, Any]:
        """Obtém métricas de um serviço específico."""
        metrics = self.metrics[service_type]
        
        return {
            "service": service_type.value,
            "total_requests": metrics.total_requests,
            "successful_requests": metrics.successful_requests,
            "failed_requests": metrics.failed_requests,
            "timeout_requests": metrics.timeout_requests,
            "success_rate": round(metrics.success_rate(), 2),
            "avg_response_time_seconds": round(metrics.avg_response_time, 2),
            "consecutive_failures": metrics.consecutive_failures,
            "circuit_breaker_open": metrics.circuit_breaker_open,
            "last_success": metrics.last_success.isoformat() if metrics.last_success else None,
            "last_failure": metrics.last_failure.isoformat() if metrics.last_failure else None
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Obtém métricas de todos os serviços."""
        return {
            "timestamp": datetime.now().isoformat(),
            "services": {
                service_type.value: self.get_service_metrics(service_type)
                for service_type in ServiceType
            },
            "summary": self._get_summary()
        }
    
    def _get_summary(self) -> Dict[str, Any]:
        """Gera resumo geral das métricas."""
        total_requests = sum(m.total_requests for m in self.metrics.values())
        total_successful = sum(m.successful_requests for m in self.metrics.values())
        total_failed = sum(m.failed_requests for m in self.metrics.values())
        
        services_with_failures = sum(1 for m in self.metrics.values() if m.consecutive_failures > 0)
        services_with_circuit_open = sum(1 for m in self.metrics.values() if m.circuit_breaker_open)
        
        overall_success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "total_requests": total_requests,
            "total_successful": total_successful,
            "total_failed": total_failed,
            "overall_success_rate": round(overall_success_rate, 2),
            "services_with_failures": services_with_failures,
            "services_with_circuit_open": services_with_circuit_open,
            "total_services": len(ServiceType)
        }
    
    def get_recent_alerts(self, hours: int = 24, level: Optional[AlertLevel] = None) -> List[Dict[str, Any]]:
        """Obtém alertas recentes."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_alerts = [
            alert for alert in self.alerts
            if alert.timestamp >= cutoff_time
        ]
        
        if level:
            recent_alerts = [alert for alert in recent_alerts if alert.level == level]
        
        return [alert.to_dict() for alert in recent_alerts]
    
    def clear_metrics(self, service_type: Optional[ServiceType] = None):
        """Limpa métricas."""
        if service_type:
            self.metrics[service_type] = ServiceMetrics(service_type=service_type)
        else:
            for st in ServiceType:
                self.metrics[st] = ServiceMetrics(service_type=st)
    
    def clear_alerts(self):
        """Limpa todos os alertas."""
        self.alerts.clear()
    
    def export_metrics(self, file_path: str):
        """Exporta métricas para arquivo JSON."""
        data = {
            "exported_at": datetime.now().isoformat(),
            "metrics": self.get_all_metrics(),
            "recent_alerts": self.get_recent_alerts()
        }
        
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📊 Métricas exportadas para {file_path}")

# Instância global do serviço de métricas
metrics_service = MetricsService() 