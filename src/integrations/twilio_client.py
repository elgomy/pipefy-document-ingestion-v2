"""
Cliente de Twilio para envío de notificaciones WhatsApp.
Maneja el envío de mensajes de WhatsApp para notificaciones de pendencias bloqueantes.
"""
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from src.config import settings
from src.utils.error_handler import with_error_handling, RetryConfig

logger = logging.getLogger(__name__)

class TwilioAPIError(Exception):
    """Excepción personalizada para errores de la API de Twilio."""
    pass

@dataclass
class FailedMessage:
    """Representa un mensaje fallido en la cola de reintentos."""
    to_number: str
    message: str
    case_id: str
    attempt_count: int = 0
    last_attempt: Optional[datetime] = None
    error_message: Optional[str] = None
    media_url: Optional[str] = None
    max_attempts: int = 3
    
    def should_retry(self) -> bool:
        """Determina si el mensaje debe ser reintentado."""
        if self.attempt_count >= self.max_attempts:
            return False
        
        if self.last_attempt is None:
            return True
            
        # Esperar al menos 5 minutos entre reintentos
        time_since_last = datetime.now() - self.last_attempt
        return time_since_last >= timedelta(minutes=5)

class TwilioClient:
    """Cliente para interactuar con la API de Twilio WhatsApp."""
    
    def __init__(self):
        """Inicializa el cliente de Twilio."""
        try:
            self.client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            self.whatsapp_number = settings.TWILIO_WHATSAPP_NUMBER
            
            # Cola de mensajes fallidos para reintentos
            self.failed_messages: List[FailedMessage] = []
            
            # Configuración de reintentos para Twilio
            self.retry_config = RetryConfig(
                max_retries=2,  # Menos reintentos para mensajes
                base_delay=3.0,
                max_delay=15.0,
                exponential_base=2.0,
                jitter=True
            )
            
            # Métricas de monitoreo
            self.message_metrics = {
                "sent": 0,
                "failed": 0,
                "retried": 0,
                "rate_limited": 0,
                "authentication_errors": 0
            }
            
            logger.info("Cliente Twilio inicializado correctamente")
        except Exception as e:
            logger.error(f"Error inicializando cliente Twilio: {e}")
            raise TwilioAPIError(f"Error de inicialización: {e}")
    
    @with_error_handling("twilio", context={"operation": "send_whatsapp_message"})
    async def send_whatsapp_message(self, to: str, message: str) -> bool:
        """
        Envía un mensaje de WhatsApp usando Twilio.
        
        Args:
            to: Número de teléfono destino (formato: +1234567890)
            message: Contenido del mensaje
            
        Returns:
            bool: True si el mensaje se envió exitosamente
        """
        try:
            # Formatear número de destino para WhatsApp
            whatsapp_to = f"whatsapp:{to}" if not to.startswith("whatsapp:") else to
            
            # Asegurar que el número FROM también tenga el prefijo whatsapp:
            whatsapp_from = f"whatsapp:{self.whatsapp_number}" if not self.whatsapp_number.startswith("whatsapp:") else self.whatsapp_number
            
            logger.info(f"Enviando WhatsApp desde {whatsapp_from} hacia {whatsapp_to}")
            
            message_obj = self.client.messages.create(
                body=message,
                from_=whatsapp_from,
                to=whatsapp_to
            )
            
            logger.info(f"✅ Mensaje WhatsApp enviado exitosamente. SID: {message_obj.sid}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Error enviando mensaje WhatsApp: {error_msg}")
            
            # Mensajes de ayuda específicos para errores comunes
            if "21211" in error_msg:  # Invalid 'To' phone number
                logger.error("💡 SOLUCIÓN: Verifica que el número destino sea válido y esté en formato internacional (+1234567890)")
            elif "21614" in error_msg:  # 'To' number is not a valid mobile number
                logger.error("💡 SOLUCIÓN: El número destino debe ser un número móvil válido")
            elif "63007" in error_msg:  # Sandbox error - recipient not joined
                logger.error("💡 SOLUCIÓN SANDBOX: El destinatario debe enviar un mensaje 'join <código>' al número sandbox +14155238886")
            elif "21608" in error_msg or "authenticate" in error_msg.lower():
                logger.error("💡 SOLUCIÓN: Verifica tus credenciales TWILIO_ACCOUNT_SID y TWILIO_AUTH_TOKEN")
            elif "21606" in error_msg:  # Trial account restrictions
                logger.error("💡 SOLUCIÓN: Actualiza tu cuenta Twilio de Trial a Paid para enviar a números no verificados")
                
            return False
    
    async def send_blocking_issues_notification(
        self,
        to_number: str,
        company_name: str,
        case_id: str,
        blocking_issues: List[str],
        cnpj: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envía una notificación específica para pendencias bloqueantes.
        
        Args:
            to_number (str): Número del gestor comercial
            company_name (str): Nome da empresa
            case_id (str): ID do caso no Pipefy
            blocking_issues (List[str]): Lista de pendencias bloqueantes
            cnpj (str, optional): CNPJ da empresa
            
        Returns:
            Dict con el resultado del envío
        """
        try:
            # Generar mensaje personalizado
            message = self._generate_blocking_issues_message(
                company_name, case_id, blocking_issues, cnpj
            )
            
            # Enviar mensaje
            result = await self.send_whatsapp_message(to_number, message, case_id=case_id)
            
            # Log específico para notificaciones de pendencias
            if result["success"]:
                logger.info(f"Notificación de pendencias enviada para caso {case_id} a {to_number}")
            else:
                logger.error(f"Falló notificación de pendencias para caso {case_id}: {result['error_message']}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error generando notificación de pendencias para caso {case_id}: {e}"
            logger.error(error_msg)
            raise TwilioAPIError(error_msg)
    
    async def send_approval_notification(
        self,
        to_number: str,
        company_name: str,
        case_id: str,
        cnpj: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envía una notificación de aprobación de documentos.
        
        Args:
            to_number (str): Número del gestor comercial
            company_name (str): Nome da empresa
            case_id (str): ID do caso no Pipefy
            cnpj (str, optional): CNPJ da empresa
            
        Returns:
            Dict con el resultado del envío
        """
        try:
            # Generar mensaje de aprobación
            message = self._generate_approval_message(company_name, case_id, cnpj)
            
            # Enviar mensaje
            result = await self.send_whatsapp_message(to_number, message, case_id=case_id)
            
            if result["success"]:
                logger.info(f"Notificación de aprobación enviada para caso {case_id} a {to_number}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error enviando notificación de aprobación para caso {case_id}: {e}"
            logger.error(error_msg)
            raise TwilioAPIError(error_msg)
    
    @with_error_handling("twilio", context={"operation": "get_message_status"})
    async def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """
        Obtiene el estado de un mensaje enviado.
        
        Args:
            message_sid (str): SID del mensaje de Twilio
            
        Returns:
            Dict con el estado del mensaje
        """
        try:
            message = self.client.messages(message_sid).fetch()
            
            return {
                "success": True,
                "message_sid": message.sid,
                "status": message.status,
                "date_created": message.date_created.isoformat() if message.date_created else None,
                "date_sent": message.date_sent.isoformat() if message.date_sent else None,
                "date_updated": message.date_updated.isoformat() if message.date_updated else None,
                "error_code": message.error_code,
                "error_message": message.error_message,
                "price": message.price,
                "price_unit": message.price_unit
            }
            
        except TwilioException as e:
            logger.error(f"Error obteniendo estado del mensaje {message_sid}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_blocking_issues_message(
        self,
        company_name: str,
        case_id: str,
        blocking_issues: List[str],
        cnpj: Optional[str] = None
    ) -> str:
        """Genera el mensaje para pendencias bloqueantes."""
        
        # Header del mensaje
        message_lines = [
            "🚫 *PENDÊNCIAS BLOQUEANTES DETECTADAS*",
            "",
            f"📋 *Caso:* {case_id}",
            f"🏢 *Empresa:* {company_name}"
        ]
        
        # Agregar CNPJ si está disponible
        if cnpj:
            message_lines.append(f"📄 *CNPJ:* {cnpj}")
        
        message_lines.extend([
            "",
            "⚠️ *Pendências identificadas:*"
        ])
        
        # Listar pendencias (máximo 5 para evitar mensajes muy largos)
        for i, issue in enumerate(blocking_issues[:5], 1):
            message_lines.append(f"{i}. {issue}")
        
        # Indicar si hay más pendencias
        if len(blocking_issues) > 5:
            message_lines.append(f"... e mais {len(blocking_issues) - 5} pendências")
        
        message_lines.extend([
            "",
            "🎯 *Ação necessária:*",
            "• Contatar o cliente para regularização",
            "• Solicitar envio dos documentos corretos",
            "• Reenviar caso após correções",
            "",
            "📱 Acesse o Pipefy para mais detalhes.",
            "",
            "_Mensagem automática do Sistema de Triagem v2.0_"
        ])
        
        return "\n".join(message_lines)
    
    def _generate_approval_message(
        self,
        company_name: str,
        case_id: str,
        cnpj: Optional[str] = None
    ) -> str:
        """Genera el mensaje para aprobación de documentos."""
        
        message_lines = [
            "✅ *DOCUMENTAÇÃO APROVADA*",
            "",
            f"📋 *Caso:* {case_id}",
            f"🏢 *Empresa:* {company_name}"
        ]
        
        if cnpj:
            message_lines.append(f"📄 *CNPJ:* {cnpj}")
        
        message_lines.extend([
            "",
            "🎉 *Resultado:* Documentação aprovada para prosseguimento!",
            "",
            "✅ Todos os requisitos foram atendidos",
            "🚀 Caso movido para próxima fase",
            "",
            "📱 Acesse o Pipefy para acompanhar o progresso.",
            "",
            "_Mensagem automática do Sistema de Triagem v2.0_"
        ])
        
        return "\n".join(message_lines)
    
    def validate_phone_number(self, phone_number: str) -> Dict[str, Any]:
        """
        Valida um número de telefone para WhatsApp.
        
        Args:
            phone_number (str): Número a validar
            
        Returns:
            Dict com resultado da validação
        """
        try:
            # Remover caracteres especiais
            clean_number = ''.join(filter(str.isdigit, phone_number))
            
            # Validações básicas
            if len(clean_number) < 10:
                return {
                    "valid": False,
                    "error": "Número muito curto"
                }
            
            if len(clean_number) > 15:
                return {
                    "valid": False,
                    "error": "Número muito longo"
                }
            
            # Formatear para padrão internacional
            if clean_number.startswith('55'):  # Brasil
                formatted_number = f"+{clean_number}"
            elif clean_number.startswith('11') or clean_number.startswith('21'):  # Códigos de área BR
                formatted_number = f"+55{clean_number}"
            else:
                formatted_number = f"+{clean_number}"
            
            return {
                "valid": True,
                "formatted_number": formatted_number,
                "original_number": phone_number
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Erro na validação: {e}"
            }
    
    def _is_retryable_error(self, error_code: Optional[int]) -> bool:
        """
        Determina si un error de Twilio es reintentable.
        
        Args:
            error_code: Código de error de Twilio
            
        Returns:
            bool: True si el error es temporal y reintentable
        """
        # Errores temporales que justifican reintentos
        retryable_codes = [
            20429,  # Rate limit exceeded
            21614,  # Message failed due to network issues  
            30001,  # Queue overflow
            30002,  # Account suspended
            30003,  # Unreachable destination handset
            30004,  # Message blocked
            30005,  # Unknown destination handset
            30006,  # Landline or unreachable carrier
            30007,  # Carrier violation
            30008,  # Unknown error
        ]
        
        return error_code in retryable_codes
    
    async def _add_to_retry_queue(
        self, 
        to_number: str, 
        message: str, 
        case_id: str, 
        error_message: str,
        media_url: Optional[str] = None
    ):
        """
        Agrega un mensaje fallido a la cola de reintentos.
        
        Args:
            to_number: Número de destino
            message: Contenido del mensaje
            case_id: ID del caso
            error_message: Mensaje de error
            media_url: URL de media (opcional)
        """
        failed_message = FailedMessage(
            to_number=to_number,
            message=message,
            case_id=case_id,
            error_message=error_message,
            media_url=media_url,
            last_attempt=datetime.now(),
            attempt_count=1
        )
        
        self.failed_messages.append(failed_message)
        logger.info(f"Mensaje agregado a cola de reintentos para caso {case_id}")
    
    async def process_retry_queue(self) -> Dict[str, Any]:
        """
        Procesa la cola de mensajes fallidos para reintentos.
        
        Returns:
            Dict con estadísticas del procesamiento
        """
        if not self.failed_messages:
            return {
                "processed": 0,
                "successful_retries": 0,
                "failed_retries": 0,
                "removed_from_queue": 0
            }
        
        processed = 0
        successful_retries = 0
        failed_retries = 0
        removed_from_queue = 0
        
        # Crear una copia de la lista para iterar
        messages_to_process = self.failed_messages.copy()
        
        for failed_message in messages_to_process:
            if not failed_message.should_retry():
                if failed_message.attempt_count >= failed_message.max_attempts:
                    logger.warning(f"Mensaje para caso {failed_message.case_id} excedió máximo de reintentos")
                    self.failed_messages.remove(failed_message)
                    removed_from_queue += 1
                continue
            
            processed += 1
            failed_message.attempt_count += 1
            failed_message.last_attempt = datetime.now()
            
            logger.info(f"Reintentando envío para caso {failed_message.case_id} (intento {failed_message.attempt_count})")
            
            # Intentar reenviar
            result = await self.send_whatsapp_message(
                to_number=failed_message.to_number,
                message=failed_message.message,
                media_url=failed_message.media_url,
                case_id=failed_message.case_id
            )
            
            if result["success"]:
                successful_retries += 1
                self.message_metrics["retried"] += 1
                self.failed_messages.remove(failed_message)
                logger.info(f"Reintento exitoso para caso {failed_message.case_id}")
            else:
                failed_retries += 1
                failed_message.error_message = result["error_message"]
                logger.warning(f"Reintento falló para caso {failed_message.case_id}: {result['error_message']}")
            
            # Pequeña pausa entre reintentos para evitar rate limiting
            await asyncio.sleep(1)
        
        return {
            "processed": processed,
            "successful_retries": successful_retries,
            "failed_retries": failed_retries,
            "removed_from_queue": removed_from_queue,
            "remaining_in_queue": len(self.failed_messages)
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Obtiene métricas del cliente de Twilio.
        
        Returns:
            Dict con métricas de uso
        """
        return {
            "message_metrics": self.message_metrics.copy(),
            "failed_queue_size": len(self.failed_messages),
            "oldest_failed_message": min(
                (msg.last_attempt for msg in self.failed_messages), 
                default=None
            ),
            "total_messages": sum(self.message_metrics.values())
        }
    
    def clear_metrics(self):
        """Reinicia las métricas del cliente."""
        self.message_metrics = {
            "sent": 0,
            "failed": 0,
            "retried": 0,
            "rate_limited": 0,
            "authentication_errors": 0
        }
        logger.info("Métricas de Twilio reiniciadas")

# Instancia global del cliente
twilio_client = TwilioClient() 