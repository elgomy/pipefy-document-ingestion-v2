"""
Servicio para manejo de base de datos Supabase.
Adaptado para usar FAQ.pdf como knowledge base en lugar de checklist_config.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from supabase import create_client, Client
from src.config.settings import settings
from src.utils.error_handler import with_error_handling, RetryConfig
import io

logger = logging.getLogger(__name__)

@dataclass
class CaseTrackingRecord:
    """Registro de tracking de caso."""
    case_id: str
    company_name: Optional[str] = None
    cnpj: Optional[str] = None
    analyst_name: Optional[str] = None
    classification_result: Optional[Dict] = None
    pipefy_card_id: Optional[str] = None
    phase_moved_to: Optional[str] = None
    processing_status: str = "pending"
    processed_at: Optional[datetime] = None

@dataclass
class ProcessingLogRecord:
    """Registro de log de procesamiento."""
    case_id: str
    log_level: str
    component: str
    message: str
    details: Optional[Dict] = None
    error_details: Optional[Dict] = None

@dataclass
class NotificationRecord:
    """Registro de notificación enviada."""
    case_id: str
    notification_type: str
    recipient_name: str
    recipient_phone: str
    message_content: str
    twilio_message_sid: Optional[str] = None
    delivery_status: str = "sent"
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None

class DatabaseService:
    """Servicio para operaciones de base de datos con Supabase."""
    
    def __init__(self):
        """Inicializa el cliente de Supabase."""
        try:
            self.client: Client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_ANON_KEY
            )
            
            # Configuración de reintentos para Supabase (crítico)
            self.retry_config = RetryConfig(
                max_retries=3,
                base_delay=2.0,
                max_delay=30.0,
                exponential_base=2.0,
                jitter=True
            )
            
            logger.info("Cliente Supabase inicializado exitosamente")
        except Exception as e:
            logger.error(f"Error al inicializar cliente Supabase: {e}")
            raise
    
    # === CASE TRACKING OPERATIONS ===
    
    @with_error_handling("supabase", context={"operation": "create_case_tracking"})
    async def create_case_tracking(self, record: CaseTrackingRecord) -> Dict:
        """
        Crea un nuevo registro de tracking de caso.
        
        Args:
            record: Datos del caso a trackear
            
        Returns:
            Registro creado con ID generado
        """
        try:
            data = asdict(record)
            # Remover campos None para evitar problemas con Supabase
            data = {k: v for k, v in data.items() if v is not None}
            
            result = self.client.table("case_tracking").insert(data).execute()
            
            if result.data:
                logger.info(f"Caso {record.case_id} creado en tracking")
                return result.data[0]
            else:
                raise Exception("No se recibieron datos del insert")
                
        except Exception as e:
            logger.error(f"Error al crear tracking de caso {record.case_id}: {e}")
            raise
    
    @with_error_handling("supabase", context={"operation": "update_case_tracking"})
    async def update_case_tracking(self, case_id: str, updates: Dict) -> Dict:
        """
        Actualiza un registro de tracking de caso.
        
        Args:
            case_id: ID del caso a actualizar
            updates: Campos a actualizar
            
        Returns:
            Registro actualizado
        """
        try:
            # Agregar timestamp de actualización
            updates["updated_at"] = datetime.now().isoformat()
            
            result = self.client.table("case_tracking").update(updates).eq("case_id", case_id).execute()
            
            if result.data:
                logger.info(f"Caso {case_id} actualizado en tracking")
                return result.data[0]
            else:
                raise Exception(f"Caso {case_id} no encontrado para actualizar")
                
        except Exception as e:
            logger.error(f"Error al actualizar tracking de caso {case_id}: {e}")
            raise
    
    async def get_case_tracking(self, case_id: str) -> Optional[Dict]:
        """
        Obtiene el registro de tracking de un caso.
        
        Args:
            case_id: ID del caso a buscar
            
        Returns:
            Registro del caso o None si no existe
        """
        try:
            result = self.client.table("case_tracking").select("*").eq("case_id", case_id).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error al obtener tracking de caso {case_id}: {e}")
            raise
    
    async def list_cases_by_status(self, status: str, limit: int = 100) -> List[Dict]:
        """
        Lista casos por status de procesamiento.
        
        Args:
            status: Status a filtrar
            limit: Límite de registros
            
        Returns:
            Lista de casos
        """
        try:
            result = (self.client.table("case_tracking")
                     .select("*")
                     .eq("processing_status", status)
                     .order("created_at", desc=True)
                     .limit(limit)
                     .execute())
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error al listar casos por status {status}: {e}")
            raise
    
    # === PROCESSING LOGS OPERATIONS ===
    
    async def add_processing_log(self, record: ProcessingLogRecord) -> Dict:
        """
        Agrega un log de procesamiento.
        
        Args:
            record: Datos del log
            
        Returns:
            Registro de log creado
        """
        try:
            data = asdict(record)
            # Remover campos None
            data = {k: v for k, v in data.items() if v is not None}
            
            result = self.client.table("processing_logs").insert(data).execute()
            
            if result.data:
                return result.data[0]
            else:
                raise Exception("No se recibieron datos del insert")
                
        except Exception as e:
            logger.error(f"Error al agregar log para caso {record.case_id}: {e}")
            raise
    
    async def get_case_logs(self, case_id: str, log_level: Optional[str] = None) -> List[Dict]:
        """
        Obtiene los logs de un caso.
        
        Args:
            case_id: ID del caso
            log_level: Filtrar por nivel de log (opcional)
            
        Returns:
            Lista de logs
        """
        try:
            query = self.client.table("processing_logs").select("*").eq("case_id", case_id)
            
            if log_level:
                query = query.eq("log_level", log_level)
            
            result = query.order("created_at", desc=True).execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error al obtener logs de caso {case_id}: {e}")
            raise
    
    # === NOTIFICATION HISTORY OPERATIONS ===
    
    async def add_notification_record(self, record: NotificationRecord) -> Dict:
        """
        Registra una notificación enviada.
        
        Args:
            record: Datos de la notificación
            
        Returns:
            Registro de notificación creado
        """
        try:
            data = asdict(record)
            # Remover campos None
            data = {k: v for k, v in data.items() if v is not None}
            
            result = self.client.table("notification_history").insert(data).execute()
            
            if result.data:
                logger.info(f"Notificación registrada para caso {record.case_id}")
                return result.data[0]
            else:
                raise Exception("No se recibieron datos del insert")
                
        except Exception as e:
            logger.error(f"Error al registrar notificación para caso {record.case_id}: {e}")
            raise
    
    async def update_notification_status(self, notification_id: str, status: str, 
                                       delivered_at: Optional[datetime] = None,
                                       error_message: Optional[str] = None) -> Dict:
        """
        Actualiza el status de una notificación.
        
        Args:
            notification_id: ID de la notificación
            status: Nuevo status
            delivered_at: Timestamp de entrega (opcional)
            error_message: Mensaje de error (opcional)
            
        Returns:
            Registro actualizado
        """
        try:
            updates = {"delivery_status": status}
            
            if delivered_at:
                updates["delivered_at"] = delivered_at.isoformat()
            if error_message:
                updates["error_message"] = error_message
            
            result = self.client.table("notification_history").update(updates).eq("id", notification_id).execute()
            
            if result.data:
                return result.data[0]
            else:
                raise Exception(f"Notificación {notification_id} no encontrada")
                
        except Exception as e:
            logger.error(f"Error al actualizar status de notificación {notification_id}: {e}")
            raise
    
    async def get_case_notifications(self, case_id: str) -> List[Dict]:
        """
        Obtiene las notificaciones de un caso.
        
        Args:
            case_id: ID del caso
            
        Returns:
            Lista de notificaciones
        """
        try:
            result = (self.client.table("notification_history")
                     .select("*")
                     .eq("case_id", case_id)
                     .order("sent_at", desc=True)
                     .execute())
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error al obtener notificaciones de caso {case_id}: {e}")
            raise
    
    # === SYSTEM CONFIG OPERATIONS ===
    
    async def get_system_config(self, config_key: str) -> Optional[Dict]:
        """
        Obtiene una configuración del sistema.
        
        Args:
            config_key: Clave de configuración
            
        Returns:
            Valor de configuración o None
        """
        try:
            result = (self.client.table("system_config")
                     .select("*")
                     .eq("config_key", config_key)
                     .eq("is_active", True)
                     .execute())
            
            if result.data:
                return result.data[0]["config_value"]
            return None
            
        except Exception as e:
            logger.error(f"Error al obtener configuración {config_key}: {e}")
            raise
    
    async def update_system_config(self, config_key: str, config_value: Dict, 
                                 description: Optional[str] = None) -> Dict:
        """
        Actualiza una configuración del sistema.
        
        Args:
            config_key: Clave de configuración
            config_value: Nuevo valor
            description: Descripción (opcional)
            
        Returns:
            Registro actualizado
        """
        try:
            updates = {"config_value": config_value}
            if description:
                updates["description"] = description
            
            result = (self.client.table("system_config")
                     .update(updates)
                     .eq("config_key", config_key)
                     .execute())
            
            if result.data:
                logger.info(f"Configuración {config_key} actualizada")
                return result.data[0]
            else:
                raise Exception(f"Configuración {config_key} no encontrada")
                
        except Exception as e:
            logger.error(f"Error al actualizar configuración {config_key}: {e}")
            raise
    
    async def get_notification_recipients(self) -> List[Dict]:
        """
        Obtiene la lista de destinatarios de notificaciones.
        
        Returns:
            Lista de destinatarios activos
        """
        try:
            recipients_config = await self.get_system_config("notification_recipients")
            if recipients_config:
                # Filtrar solo destinatarios activos
                return [r for r in recipients_config if r.get("is_active", True)]
            return []
            
        except Exception as e:
            logger.error(f"Error al obtener destinatarios de notificaciones: {e}")
            raise
    
    # === UTILITY METHODS ===
    
    async def health_check(self) -> bool:
        """
        Verifica la conectividad con Supabase.
        
        Returns:
            True si la conexión es exitosa
        """
        try:
            # Intentar una consulta simple
            result = self.client.table("system_config").select("count").execute()
            return True
        except Exception as e:
            logger.error(f"Health check falló: {e}")
            return False
    
    async def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """
        Limpia logs antiguos basado en configuración de retención.
        
        Args:
            days_to_keep: Días de logs a mantener
            
        Returns:
            Número de registros eliminados
        """
        try:
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_to_keep)
            
            result = (self.client.table("processing_logs")
                     .delete()
                     .lt("created_at", cutoff_date.isoformat())
                     .execute())
            
            deleted_count = len(result.data) if result.data else 0
            logger.info(f"Limpieza completada: {deleted_count} logs eliminados")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error en limpieza de logs: {e}")
            raise
    
    # === DOCUMENT STORAGE OPERATIONS ===
    
    @with_error_handling("supabase", context={"operation": "upload_file_to_storage"})
    async def upload_file_to_storage(self, file_content: bytes, file_path: str, content_type: str = "application/pdf") -> Dict[str, Any]:
        """
        Sube un archivo al bucket 'documents' de Supabase Storage.
        
        Args:
            file_content: Contenido del archivo en bytes
            file_path: Ruta donde guardar el archivo en el bucket
            content_type: Tipo de contenido del archivo
            
        Returns:
            Información del archivo subido
            
        Raises:
            Exception: Si no se puede subir el archivo
        """
        try:
            logger.info(f"Subiendo archivo a storage: {file_path}")
            
            # Subir archivo al bucket 'documents'
            result = self.client.storage.from_("documents").upload(
                path=file_path,
                file=file_content,
                file_options={
                    "content-type": content_type,
                    "upsert": "true"  # Sobrescribir si ya existe
                }
            )
            
            if result:
                # Obtener URL pública del archivo
                public_url = self.client.storage.from_("documents").get_public_url(file_path)
                
                logger.info(f"Archivo subido exitosamente: {file_path}")
                
                return {
                    "success": True,
                    "file_path": file_path,
                    "public_url": public_url,
                    "file_size_bytes": len(file_content),
                    "content_type": content_type,
                    "uploaded_at": datetime.now().isoformat()
                }
            else:
                raise Exception("No se recibió confirmación de subida")
                
        except Exception as e:
            logger.error(f"Error al subir archivo {file_path}: {e}")
            raise
    
    @with_error_handling("supabase", context={"operation": "create_document_record"})
    async def create_document_record(self, 
                                   name: str,
                                   case_id: str,
                                   document_tag: str,
                                   file_url: str,
                                   pipe_id: Optional[str] = None,
                                   metadata: Optional[Dict] = None,
                                   status: str = "uploaded") -> Dict[str, Any]:
        """
        Crea un registro en la tabla 'documents'.
        
        Args:
            name: Nombre descriptivo del documento
            case_id: ID del caso/card de Pipefy
            document_tag: Tipo/categoría del documento
            file_url: URL del archivo en Supabase Storage
            pipe_id: ID del pipe de Pipefy (opcional)
            metadata: Metadatos adicionales (opcional)
            status: Estado del documento
            
        Returns:
            Registro creado
            
        Raises:
            Exception: Si no se puede crear el registro
        """
        try:
            document_data = {
                "name": name,
                "case_id": case_id,
                "document_tag": document_tag,
                "file_url": file_url,
                "status": status,
                "metadata": metadata or {},
                "processed_by_crew": False
            }
            
            if pipe_id:
                document_data["pipe_id"] = pipe_id
            
            logger.info(f"Creando registro de documento: {name} para caso {case_id}")
            
            result = self.client.table("documents").insert(document_data).execute()
            
            if result.data:
                logger.info(f"Documento registrado exitosamente: {result.data[0]['id']}")
                return result.data[0]
            else:
                raise Exception("No se recibieron datos del insert")
                
        except Exception as e:
            logger.error(f"Error al crear registro de documento {name}: {e}")
            raise
    
    async def upload_and_register_document(self,
                                         file_content: bytes,
                                         file_name: str,
                                         case_id: str,
                                         document_tag: str,
                                         pipe_id: Optional[str] = None,
                                         content_type: str = "application/pdf",
                                         metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Sube un archivo a storage y crea su registro en la tabla documents.
        
        Args:
            file_content: Contenido del archivo en bytes
            file_name: Nombre del archivo
            case_id: ID del caso/card de Pipefy
            document_tag: Tipo/categoría del documento
            pipe_id: ID del pipe de Pipefy (opcional)
            content_type: Tipo de contenido del archivo
            metadata: Metadatos adicionales (opcional)
            
        Returns:
            Información completa del documento subido y registrado
            
        Raises:
            Exception: Si falla alguna operación
        """
        try:
            # Construir ruta del archivo en el bucket
            # Estructura: case_id/document_tag_timestamp.extension
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_extension = file_name.split('.')[-1] if '.' in file_name else 'pdf'
            storage_path = f"{case_id}/{document_tag}_{timestamp}.{file_extension}"
            
            logger.info(f"Procesando documento {file_name} para caso {case_id}")
            
            # 1. Subir archivo a storage
            upload_result = await self.upload_file_to_storage(
                file_content=file_content,
                file_path=storage_path,
                content_type=content_type
            )
            
            if not upload_result["success"]:
                raise Exception("Falló la subida del archivo")
            
            # 2. Crear registro en tabla documents
            document_record = await self.create_document_record(
                name=file_name,
                case_id=case_id,
                document_tag=document_tag,
                file_url=upload_result["public_url"],
                pipe_id=pipe_id,
                metadata={
                    **(metadata or {}),
                    "file_size_bytes": upload_result["file_size_bytes"],
                    "storage_path": storage_path,
                    "uploaded_at": upload_result["uploaded_at"]
                }
            )
            
            logger.info(f"Documento {file_name} procesado exitosamente para caso {case_id}")
            
            return {
                "success": True,
                "document_id": document_record["id"],
                "storage_path": storage_path,
                "public_url": upload_result["public_url"],
                "file_size_bytes": upload_result["file_size_bytes"],
                "document_record": document_record,
                "upload_result": upload_result
            }
            
        except Exception as e:
            logger.error(f"Error al procesar documento {file_name} para caso {case_id}: {e}")
            raise
    
    async def get_case_documents(self, case_id: str) -> List[Dict]:
        """
        Obtiene todos los documentos de un caso.
        
        Args:
            case_id: ID del caso
            
        Returns:
            Lista de documentos del caso
        """
        try:
            result = (self.client.table("documents")
                     .select("*")
                     .eq("case_id", case_id)
                     .order("created_at", desc=True)
                     .execute())
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error al obtener documentos de caso {case_id}: {e}")
            raise

# Instancia global del servicio
database_service = DatabaseService()