"""
Servicio para gestión de destinatarios de notificaciones.
Maneja el CRUD de destinatarios y validación de números de teléfono.
"""
import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime

from src.integrations.twilio_client import twilio_client
from src.services.notification_service import NotificationRecipient

logger = logging.getLogger(__name__)

class RecipientService:
    """Servicio para gestión de destinatarios de notificaciones."""
    
    def __init__(self, supabase_client):
        """
        Inicializa el servicio de gestión de destinatarios.
        
        Args:
            supabase_client: Cliente de Supabase
        """
        self.client = supabase_client
        self.twilio_client = twilio_client
        self.table = "notification_recipients"
    
    async def create_recipient(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea un nuevo destinatario.
        
        Args:
            data: Datos del destinatario
            
        Returns:
            Dict: Datos del destinatario creado
            
        Raises:
            ValueError: Si el número de teléfono no es válido
        """
        # Validar número de teléfono con Twilio
        if not await self.twilio_client.validate_phone_number(data["phone_number"]):
            raise ValueError(f"Número de teléfono inválido: {data['phone_number']}")
        
        try:
            result = await self.client.table(self.table).insert(data).execute()
            return result.data[0]
        except Exception as e:
            logger.error(f"Error al crear destinatario: {e}")
            raise
    
    async def get_recipient(self, recipient_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Obtiene un destinatario por ID.
        
        Args:
            recipient_id: ID del destinatario
            
        Returns:
            Dict: Datos del destinatario o None si no existe
        """
        try:
            result = await self.client.table(self.table)\
                .select("*")\
                .eq("id", str(recipient_id))\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error al obtener destinatario {recipient_id}: {e}")
            raise
    
    async def list_recipients(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Lista todos los destinatarios.
        
        Args:
            active_only: Si True, solo retorna destinatarios activos
            
        Returns:
            List[Dict]: Lista de destinatarios
        """
        try:
            query = self.client.table(self.table).select("*")
            if active_only:
                query = query.eq("is_active", True)
            result = await query.execute()
            return result.data
        except Exception as e:
            logger.error(f"Error al listar destinatarios: {e}")
            raise
    
    async def get_recipients_by_role(self, role: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Obtiene destinatarios por rol.
        
        Args:
            role: Rol a filtrar
            active_only: Si True, solo retorna destinatarios activos
            
        Returns:
            List[Dict]: Lista de destinatarios con el rol especificado
        """
        try:
            query = self.client.table(self.table)\
                .select("*")\
                .eq("role", role)
            if active_only:
                query = query.eq("is_active", True)
            result = await query.execute()
            return result.data
        except Exception as e:
            logger.error(f"Error al obtener destinatarios por rol {role}: {e}")
            raise
    
    async def get_recipients_by_company(self, company: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Obtiene destinatarios por empresa.
        
        Args:
            company: Empresa a filtrar
            active_only: Si True, solo retorna destinatarios activos
            
        Returns:
            List[Dict]: Lista de destinatarios de la empresa especificada
        """
        try:
            query = self.client.table(self.table)\
                .select("*")\
                .eq("company_name", company)
            if active_only:
                query = query.eq("is_active", True)
            result = await query.execute()
            return result.data
        except Exception as e:
            logger.error(f"Error al obtener destinatarios por empresa {company}: {e}")
            raise
    
    async def update_recipient(self, recipient_id: UUID, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualiza un destinatario.
        
        Args:
            recipient_id: ID del destinatario
            updates: Datos a actualizar
            
        Returns:
            Dict: Datos del destinatario actualizado
            
        Raises:
            ValueError: Si el número de teléfono no es válido
        """
        # Validar número de teléfono si se está actualizando
        if "phone_number" in updates:
            if not await self.twilio_client.validate_phone_number(updates["phone_number"]):
                raise ValueError(f"Número de teléfono inválido: {updates['phone_number']}")
        
        try:
            updates["updated_at"] = datetime.utcnow()
            result = await self.client.table(self.table)\
                .update(updates)\
                .eq("id", str(recipient_id))\
                .execute()
            return result.data[0]
        except Exception as e:
            logger.error(f"Error al actualizar destinatario {recipient_id}: {e}")
            raise
    
    async def delete_recipient(self, recipient_id: UUID) -> bool:
        """
        Elimina un destinatario.
        
        Args:
            recipient_id: ID del destinatario
            
        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            result = await self.client.table(self.table)\
                .delete()\
                .eq("id", str(recipient_id))\
                .execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error al eliminar destinatario {recipient_id}: {e}")
            raise
    
    async def deactivate_recipient(self, recipient_id: UUID) -> Dict[str, Any]:
        """
        Desactiva un destinatario.
        
        Args:
            recipient_id: ID del destinatario
            
        Returns:
            Dict: Datos del destinatario actualizado
        """
        return await self.update_recipient(recipient_id, {"is_active": False})
    
    async def activate_recipient(self, recipient_id: UUID) -> Dict[str, Any]:
        """
        Activa un destinatario.
        
        Args:
            recipient_id: ID del destinatario
            
        Returns:
            Dict: Datos del destinatario actualizado
        """
        return await self.update_recipient(recipient_id, {"is_active": True})
    
    def to_notification_recipient(self, data: Dict[str, Any]) -> NotificationRecipient:
        """
        Convierte datos de la base de datos a NotificationRecipient.
        
        Args:
            data: Datos del destinatario
            
        Returns:
            NotificationRecipient
        """
        return NotificationRecipient(
            name=data["name"],
            phone_number=data["phone_number"],
            role=data["role"],
            company_name=data.get("company_name")
        ) 