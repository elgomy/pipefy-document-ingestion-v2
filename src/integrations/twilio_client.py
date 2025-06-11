"""
Cliente de Twilio para envío de notificaciones WhatsApp.
Maneja el envío de mensajes de WhatsApp para notificaciones de pendencias bloqueantes.
"""
import logging
from typing import Dict, Any, Optional, List
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from src.config import settings
from src.utils.error_handler import with_error_handling, RetryConfig

logger = logging.getLogger(__name__)

class TwilioAPIError(Exception):
    """Excepción personalizada para errores de la API de Twilio."""
    pass

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
            
            # Configuración de reintentos para Twilio
            self.retry_config = RetryConfig(
                max_retries=2,  # Menos reintentos para mensajes
                base_delay=3.0,
                max_delay=15.0,
                exponential_base=2.0,
                jitter=True
            )
            
            logger.info("Cliente Twilio inicializado correctamente")
        except Exception as e:
            logger.error(f"Error inicializando cliente Twilio: {e}")
            raise TwilioAPIError(f"Error de inicialización: {e}")
    
    @with_error_handling("twilio", context={"operation": "send_whatsapp_message"})
    async def send_whatsapp_message(
        self,
        to_number: str,
        message: str,
        media_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envía un mensaje de WhatsApp a un número específico.
        
        Args:
            to_number (str): Número de destino en formato internacional (+5511999999999)
            message (str): Contenido del mensaje
            media_url (str, optional): URL de media para adjuntar
            
        Returns:
            Dict con el resultado del envío
        """
        try:
            # Validar formato del número
            if not to_number.startswith('+'):
                to_number = f"+{to_number}"
            
            # Formatear número para WhatsApp
            whatsapp_to = f"whatsapp:{to_number}"
            whatsapp_from = f"whatsapp:{self.whatsapp_number}"
            
            # Preparar parámetros del mensaje
            message_params = {
                'body': message,
                'from_': whatsapp_from,
                'to': whatsapp_to
            }
            
            # Agregar media si se proporciona
            if media_url:
                message_params['media_url'] = [media_url]
            
            # Enviar mensaje
            logger.info(f"Enviando WhatsApp a {to_number}")
            twilio_message = self.client.messages.create(**message_params)
            
            result = {
                "success": True,
                "message_sid": twilio_message.sid,
                "status": twilio_message.status,
                "to_number": to_number,
                "from_number": self.whatsapp_number,
                "message_body": message,
                "error_code": None,
                "error_message": None
            }
            
            logger.info(f"WhatsApp enviado exitosamente. SID: {twilio_message.sid}")
            return result
            
        except TwilioException as e:
            error_msg = f"Error de Twilio enviando WhatsApp a {to_number}: {e}"
            logger.error(error_msg)
            
            return {
                "success": False,
                "message_sid": None,
                "status": "failed",
                "to_number": to_number,
                "from_number": self.whatsapp_number,
                "message_body": message,
                "error_code": getattr(e, 'code', None),
                "error_message": str(e)
            }
            
        except Exception as e:
            error_msg = f"Error inesperado enviando WhatsApp a {to_number}: {e}"
            logger.error(error_msg)
            
            return {
                "success": False,
                "message_sid": None,
                "status": "failed",
                "to_number": to_number,
                "from_number": self.whatsapp_number,
                "message_body": message,
                "error_code": "UNKNOWN_ERROR",
                "error_message": str(e)
            }
    
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
            result = await self.send_whatsapp_message(to_number, message)
            
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
            result = await self.send_whatsapp_message(to_number, message)
            
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

# Instancia global del cliente
twilio_client = TwilioClient() 