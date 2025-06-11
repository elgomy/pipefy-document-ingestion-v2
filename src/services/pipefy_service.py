"""
Servicio de alto nivel para operaciones de Pipefy.
Orquesta el movimiento de cards y actualización de campos.
"""
import logging
from typing import Dict, Any, Optional
from src.integrations.pipefy_client import pipefy_client, PipefyAPIError
from src.config import settings

logger = logging.getLogger(__name__)

class PipefyService:
    """Servicio para operaciones de alto nivel en Pipefy."""
    
    def __init__(self):
        self.client = pipefy_client
    
    async def process_triagem_result(
        self, 
        card_id: str, 
        classification: str, 
        detailed_report: str,
        summary_report: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Procesa el resultado de la triagem: mueve el card y actualiza los informes.
        
        Args:
            card_id (str): ID del card de Pipefy
            classification (str): Clasificación de la IA (Aprovado, Pendencia_Bloqueante, Pendencia_NaoBloqueante)
            detailed_report (str): Informe detallado en formato Markdown
            summary_report (str, optional): Informe resumido para campo específico
            
        Returns:
            Dict con el resultado de todas las operaciones
        """
        results = {
            "card_id": card_id,
            "classification": classification,
            "operations": [],
            "success": True,
            "errors": []
        }
        
        try:
            # 1. Mover card a la fase correspondiente
            logger.info(f"Procesando triagem para card {card_id} con clasificación '{classification}'")
            
            move_result = await self.client.move_card_by_classification(card_id, classification)
            results["operations"].append({
                "type": "move_card",
                "success": move_result["success"],
                "new_phase_id": move_result["new_phase_id"],
                "new_phase_name": move_result["new_phase_name"]
            })
            
            # 2. Actualizar campo con el informe detallado
            update_result = await self.client.update_card_field(
                card_id, 
                settings.FIELD_ID_INFORME, 
                detailed_report
            )
            results["operations"].append({
                "type": "update_detailed_report",
                "success": update_result["success"],
                "field_id": settings.FIELD_ID_INFORME
            })
            
            # 3. Actualizar campo con el informe resumido (si existe)
            if summary_report and hasattr(settings, 'FIELD_ID_SUMMARY_INFORME'):
                summary_update_result = await self.client.update_card_field(
                    card_id, 
                    settings.FIELD_ID_SUMMARY_INFORME, 
                    summary_report
                )
                results["operations"].append({
                    "type": "update_summary_report",
                    "success": summary_update_result["success"],
                    "field_id": settings.FIELD_ID_SUMMARY_INFORME
                })
            
            logger.info(f"Triagem procesada exitosamente para card {card_id}")
            
        except PipefyAPIError as e:
            error_msg = f"Error de API Pipefy para card {card_id}: {str(e)}"
            logger.error(error_msg)
            results["success"] = False
            results["errors"].append(error_msg)
            
        except ValueError as e:
            error_msg = f"Error de validación para card {card_id}: {str(e)}"
            logger.error(error_msg)
            results["success"] = False
            results["errors"].append(error_msg)
            
        except Exception as e:
            error_msg = f"Error inesperado procesando card {card_id}: {str(e)}"
            logger.error(error_msg)
            results["success"] = False
            results["errors"].append(error_msg)
        
        return results
    
    async def move_card_to_phase(self, card_id: str, phase_id: str) -> Dict[str, Any]:
        """
        Mueve un card a una fase específica.
        
        Args:
            card_id (str): ID del card
            phase_id (str): ID de la fase destino
            
        Returns:
            Dict con el resultado de la operación
        """
        try:
            result = await self.client.move_card_to_phase(card_id, phase_id)
            logger.info(f"Card {card_id} movido a fase {phase_id}")
            return result
        except Exception as e:
            logger.error(f"Error moviendo card {card_id} a fase {phase_id}: {str(e)}")
            raise
    
    async def update_card_informe(self, card_id: str, informe_markdown: str) -> Dict[str, Any]:
        """
        Actualiza el campo de informe de triagem en un card.
        
        Args:
            card_id (str): ID del card
            informe_markdown (str): Informe en formato Markdown
            
        Returns:
            Dict con el resultado de la operación
        """
        try:
            result = await self.client.update_card_field(
                card_id, 
                settings.FIELD_ID_INFORME, 
                informe_markdown
            )
            logger.info(f"Informe actualizado para card {card_id}")
            return result
        except Exception as e:
            logger.error(f"Error actualizando informe para card {card_id}: {str(e)}")
            raise
    
    async def get_card_status(self, card_id: str) -> Dict[str, Any]:
        """
        Obtiene el estado actual de un card.
        
        Args:
            card_id (str): ID del card
            
        Returns:
            Dict con la información del card
        """
        try:
            card_info = await self.client.get_card_info(card_id)
            logger.info(f"Información obtenida para card {card_id}")
            return card_info
        except Exception as e:
            logger.error(f"Error obteniendo información del card {card_id}: {str(e)}")
            raise
    
    async def validate_card_exists(self, card_id: str) -> bool:
        """
        Valida que un card existe en Pipefy.
        
        Args:
            card_id (str): ID del card a validar
            
        Returns:
            bool: True si el card existe, False en caso contrario
        """
        try:
            await self.client.get_card_info(card_id)
            return True
        except PipefyAPIError:
            return False
        except Exception as e:
            logger.error(f"Error validando existencia del card {card_id}: {str(e)}")
            return False


# Instancia global del servicio
pipefy_service = PipefyService()