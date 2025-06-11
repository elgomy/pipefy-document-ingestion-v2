"""
Servicio de notificaciones para el sistema de triagem documental.
Maneja el envío de notificaciones WhatsApp para diferentes eventos del sistema.
"""
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.integrations.twilio_client import twilio_client, TwilioAPIError
from src.services.classification_service import ClassificationResult, ClassificationType

logger = logging.getLogger(__name__)

class NotificationType(Enum):
    """Tipos de notificaciones disponibles."""
    BLOCKING_ISSUES = "blocking_issues"
    APPROVAL = "approval"
    NON_BLOCKING_ISSUES = "non_blocking_issues"
    SYSTEM_ERROR = "system_error"

@dataclass
class NotificationRecipient:
    """Información del destinatario de la notificación."""
    name: str
    phone_number: str
    role: str = "gestor_comercial"
    is_active: bool = True

@dataclass
class NotificationContext:
    """Contexto para generar notificaciones."""
    case_id: str
    company_name: str
    cnpj: Optional[str] = None
    analyst_name: Optional[str] = None
    classification_result: Optional[ClassificationResult] = None
    additional_info: Optional[Dict[str, Any]] = None

@dataclass
class NotificationResult:
    """Resultado del envío de notificación."""
    success: bool
    notification_type: NotificationType
    recipient: NotificationRecipient
    message_sid: Optional[str] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None

class NotificationService:
    """Servicio para envío de notificaciones WhatsApp."""
    
    def __init__(self):
        """Inicializa el servicio de notificaciones."""
        self.twilio_client = twilio_client
        logger.info("Servicio de notificaciones inicializado")
    
    async def send_classification_notification(
        self,
        classification_result: ClassificationResult,
        context: NotificationContext,
        recipient: NotificationRecipient
    ) -> NotificationResult:
        """
        Envía notificación basada en el resultado de clasificación.
        
        Args:
            classification_result: Resultado de la clasificación
            context: Contexto del caso
            recipient: Destinatario de la notificación
            
        Returns:
            NotificationResult con el resultado del envío
        """
        try:
            # Determinar tipo de notificación basado en clasificación
            if classification_result.classification == ClassificationType.APROVADO:
                return await self._send_approval_notification(context, recipient)
            
            elif classification_result.classification == ClassificationType.PENDENCIA_BLOQUEANTE:
                return await self._send_blocking_issues_notification(
                    classification_result, context, recipient
                )
            
            elif classification_result.classification == ClassificationType.PENDENCIA_NAO_BLOQUEANTE:
                return await self._send_non_blocking_issues_notification(
                    classification_result, context, recipient
                )
            
            else:
                raise ValueError(f"Tipo de classificação não suportado: {classification_result.classification}")
                
        except Exception as e:
            error_msg = f"Error enviando notificación de clasificación: {e}"
            logger.error(error_msg)
            
            return NotificationResult(
                success=False,
                notification_type=NotificationType.SYSTEM_ERROR,
                recipient=recipient,
                error_message=error_msg,
                sent_at=datetime.now()
            )
    
    async def _send_blocking_issues_notification(
        self,
        classification_result: ClassificationResult,
        context: NotificationContext,
        recipient: NotificationRecipient
    ) -> NotificationResult:
        """Envía notificación para pendencias bloqueantes."""
        try:
            # Validar número de teléfono
            phone_validation = self.twilio_client.validate_phone_number(recipient.phone_number)
            if not phone_validation["valid"]:
                raise ValueError(f"Número de teléfono inválido: {phone_validation['error']}")
            
            # Enviar notificación
            result = await self.twilio_client.send_blocking_issues_notification(
                to_number=phone_validation["formatted_number"],
                company_name=context.company_name,
                case_id=context.case_id,
                blocking_issues=classification_result.blocking_issues,
                cnpj=context.cnpj
            )
            
            # Crear resultado
            notification_result = NotificationResult(
                success=result["success"],
                notification_type=NotificationType.BLOCKING_ISSUES,
                recipient=recipient,
                message_sid=result.get("message_sid"),
                error_message=result.get("error_message"),
                sent_at=datetime.now()
            )
            
            # Log del resultado
            if result["success"]:
                logger.info(f"Notificación de pendencias bloqueantes enviada exitosamente para caso {context.case_id}")
            else:
                logger.error(f"Falló envío de notificación para caso {context.case_id}: {result['error_message']}")
            
            return notification_result
            
        except Exception as e:
            error_msg = f"Error enviando notificación de pendencias bloqueantes: {e}"
            logger.error(error_msg)
            
            return NotificationResult(
                success=False,
                notification_type=NotificationType.BLOCKING_ISSUES,
                recipient=recipient,
                error_message=error_msg,
                sent_at=datetime.now()
            )
    
    async def _send_approval_notification(
        self,
        context: NotificationContext,
        recipient: NotificationRecipient
    ) -> NotificationResult:
        """Envía notificación de aprobación."""
        try:
            # Validar número de teléfono
            phone_validation = self.twilio_client.validate_phone_number(recipient.phone_number)
            if not phone_validation["valid"]:
                raise ValueError(f"Número de teléfono inválido: {phone_validation['error']}")
            
            # Enviar notificación
            result = await self.twilio_client.send_approval_notification(
                to_number=phone_validation["formatted_number"],
                company_name=context.company_name,
                case_id=context.case_id,
                cnpj=context.cnpj
            )
            
            # Crear resultado
            notification_result = NotificationResult(
                success=result["success"],
                notification_type=NotificationType.APPROVAL,
                recipient=recipient,
                message_sid=result.get("message_sid"),
                error_message=result.get("error_message"),
                sent_at=datetime.now()
            )
            
            if result["success"]:
                logger.info(f"Notificación de aprobación enviada exitosamente para caso {context.case_id}")
            
            return notification_result
            
        except Exception as e:
            error_msg = f"Error enviando notificación de aprobación: {e}"
            logger.error(error_msg)
            
            return NotificationResult(
                success=False,
                notification_type=NotificationType.APPROVAL,
                recipient=recipient,
                error_message=error_msg,
                sent_at=datetime.now()
            )
    
    async def _send_non_blocking_issues_notification(
        self,
        classification_result: ClassificationResult,
        context: NotificationContext,
        recipient: NotificationRecipient
    ) -> NotificationResult:
        """Envía notificación para pendencias no bloqueantes."""
        try:
            # Para pendencias no bloqueantes, enviamos un mensaje informativo
            message = self._generate_non_blocking_message(
                context.company_name,
                context.case_id,
                classification_result.non_blocking_issues,
                classification_result.auto_generate_actions,
                context.cnpj
            )
            
            # Validar número de teléfono
            phone_validation = self.twilio_client.validate_phone_number(recipient.phone_number)
            if not phone_validation["valid"]:
                raise ValueError(f"Número de teléfono inválido: {phone_validation['error']}")
            
            # Enviar mensaje
            result = await self.twilio_client.send_whatsapp_message(
                to_number=phone_validation["formatted_number"],
                message=message
            )
            
            # Crear resultado
            notification_result = NotificationResult(
                success=result["success"],
                notification_type=NotificationType.NON_BLOCKING_ISSUES,
                recipient=recipient,
                message_sid=result.get("message_sid"),
                error_message=result.get("error_message"),
                sent_at=datetime.now()
            )
            
            if result["success"]:
                logger.info(f"Notificación de pendencias no bloqueantes enviada para caso {context.case_id}")
            
            return notification_result
            
        except Exception as e:
            error_msg = f"Error enviando notificación de pendencias no bloqueantes: {e}"
            logger.error(error_msg)
            
            return NotificationResult(
                success=False,
                notification_type=NotificationType.NON_BLOCKING_ISSUES,
                recipient=recipient,
                error_message=error_msg,
                sent_at=datetime.now()
            )
    
    async def send_custom_notification(
        self,
        recipient: NotificationRecipient,
        message: str,
        notification_type: NotificationType = NotificationType.SYSTEM_ERROR
    ) -> NotificationResult:
        """
        Envía una notificación personalizada.
        
        Args:
            recipient: Destinatario
            message: Mensaje a enviar
            notification_type: Tipo de notificación
            
        Returns:
            NotificationResult con el resultado
        """
        try:
            # Validar número de teléfono
            phone_validation = self.twilio_client.validate_phone_number(recipient.phone_number)
            if not phone_validation["valid"]:
                raise ValueError(f"Número de teléfono inválido: {phone_validation['error']}")
            
            # Enviar mensaje
            result = await self.twilio_client.send_whatsapp_message(
                to_number=phone_validation["formatted_number"],
                message=message
            )
            
            return NotificationResult(
                success=result["success"],
                notification_type=notification_type,
                recipient=recipient,
                message_sid=result.get("message_sid"),
                error_message=result.get("error_message"),
                sent_at=datetime.now()
            )
            
        except Exception as e:
            error_msg = f"Error enviando notificación personalizada: {e}"
            logger.error(error_msg)
            
            return NotificationResult(
                success=False,
                notification_type=notification_type,
                recipient=recipient,
                error_message=error_msg,
                sent_at=datetime.now()
            )
    
    async def get_notification_status(self, message_sid: str) -> Dict[str, Any]:
        """
        Obtiene el estado de una notificación enviada.
        
        Args:
            message_sid: SID del mensaje de Twilio
            
        Returns:
            Dict con el estado del mensaje
        """
        try:
            return await self.twilio_client.get_message_status(message_sid)
        except Exception as e:
            logger.error(f"Error obteniendo estado de notificación {message_sid}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_non_blocking_message(
        self,
        company_name: str,
        case_id: str,
        non_blocking_issues: List[str],
        auto_actions: List[str],
        cnpj: Optional[str] = None
    ) -> str:
        """Genera mensaje para pendencias no bloqueantes."""
        
        message_lines = [
            "⚠️ *PENDÊNCIAS NÃO BLOQUEANTES*",
            "",
            f"📋 *Caso:* {case_id}",
            f"🏢 *Empresa:* {company_name}"
        ]
        
        if cnpj:
            message_lines.append(f"📄 *CNPJ:* {cnpj}")
        
        message_lines.extend([
            "",
            "✅ *Status:* Documentação aprovada com observações",
            ""
        ])
        
        # Listar pendencias no bloqueantes
        if non_blocking_issues:
            message_lines.append("📝 *Observações:*")
            for i, issue in enumerate(non_blocking_issues[:3], 1):
                message_lines.append(f"{i}. {issue}")
            
            if len(non_blocking_issues) > 3:
                message_lines.append(f"... e mais {len(non_blocking_issues) - 3} observações")
            
            message_lines.append("")
        
        # Listar ações automáticas
        if auto_actions:
            message_lines.append("🤖 *Ações automáticas disponíveis:*")
            for action in auto_actions[:3]:
                message_lines.append(f"• {action}")
            
            if len(auto_actions) > 3:
                message_lines.append(f"• ... e mais {len(auto_actions) - 3} ações")
            
            message_lines.append("")
        
        message_lines.extend([
            "🚀 Caso prosseguindo para próxima fase",
            "",
            "📱 Acesse o Pipefy para mais detalhes.",
            "",
            "_Mensagem automática do Sistema de Triagem v2.0_"
        ])
        
        return "\n".join(message_lines)
    
    def validate_recipient(self, recipient: NotificationRecipient) -> Dict[str, Any]:
        """
        Valida um destinatário de notificação.
        
        Args:
            recipient: Destinatário a validar
            
        Returns:
            Dict com resultado da validação
        """
        try:
            # Validar campos obrigatórios
            if not recipient.name or not recipient.name.strip():
                return {
                    "valid": False,
                    "error": "Nome do destinatário é obrigatório"
                }
            
            if not recipient.phone_number or not recipient.phone_number.strip():
                return {
                    "valid": False,
                    "error": "Número de telefone é obrigatório"
                }
            
            # Validar número de telefone
            phone_validation = self.twilio_client.validate_phone_number(recipient.phone_number)
            if not phone_validation["valid"]:
                return {
                    "valid": False,
                    "error": f"Número de telefone inválido: {phone_validation['error']}"
                }
            
            # Validar se está ativo
            if not recipient.is_active:
                return {
                    "valid": False,
                    "error": "Destinatário está inativo"
                }
            
            return {
                "valid": True,
                "formatted_phone": phone_validation["formatted_number"]
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Erro na validação: {e}"
            }

# Instancia global del servicio
notification_service = NotificationService() 