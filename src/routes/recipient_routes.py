"""
Rutas API para gestión de destinatarios de notificaciones.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, constr

from src.services.recipient_service import RecipientService
from src.dependencies import get_supabase_client

router = APIRouter(prefix="/recipients", tags=["recipients"])

class RecipientCreate(BaseModel):
    """Modelo para crear destinatario."""
    name: constr(min_length=1, max_length=100)
    phone_number: constr(min_length=10, max_length=15)
    role: constr(min_length=1, max_length=50) = "gestor_comercial"
    company_name: Optional[str] = None

class RecipientUpdate(BaseModel):
    """Modelo para actualizar destinatario."""
    name: Optional[constr(min_length=1, max_length=100)] = None
    phone_number: Optional[constr(min_length=10, max_length=15)] = None
    role: Optional[constr(min_length=1, max_length=50)] = None
    company_name: Optional[str] = None
    is_active: Optional[bool] = None

class RecipientResponse(BaseModel):
    """Modelo de respuesta para destinatario."""
    id: UUID
    name: str
    phone_number: str
    role: str
    company_name: Optional[str]
    is_active: bool

@router.post("/", response_model=RecipientResponse, status_code=status.HTTP_201_CREATED)
async def create_recipient(
    recipient: RecipientCreate,
    supabase = Depends(get_supabase_client)
) -> RecipientResponse:
    """
    Crea un nuevo destinatario.
    
    Args:
        recipient: Datos del destinatario a crear
        supabase: Cliente Supabase (inyectado)
        
    Returns:
        RecipientResponse: Destinatario creado
        
    Raises:
        HTTPException: Si hay error en la validación o creación
    """
    try:
        service = RecipientService(supabase)
        result = await service.create_recipient(recipient.model_dump())
        return RecipientResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear destinatario: {str(e)}"
        )

@router.get("/{recipient_id}", response_model=RecipientResponse)
async def get_recipient(
    recipient_id: UUID,
    supabase = Depends(get_supabase_client)
) -> RecipientResponse:
    """
    Obtiene un destinatario por ID.
    
    Args:
        recipient_id: ID del destinatario
        supabase: Cliente Supabase (inyectado)
        
    Returns:
        RecipientResponse: Datos del destinatario
        
    Raises:
        HTTPException: Si el destinatario no existe
    """
    try:
        service = RecipientService(supabase)
        result = await service.get_recipient(recipient_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Destinatario {recipient_id} no encontrado"
            )
        return RecipientResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener destinatario: {str(e)}"
        )

@router.get("/", response_model=List[RecipientResponse])
async def list_recipients(
    active_only: bool = True,
    role: Optional[str] = None,
    company: Optional[str] = None,
    supabase = Depends(get_supabase_client)
) -> List[RecipientResponse]:
    """
    Lista destinatarios con filtros opcionales.
    
    Args:
        active_only: Si True, solo retorna destinatarios activos
        role: Filtrar por rol
        company: Filtrar por empresa
        supabase: Cliente Supabase (inyectado)
        
    Returns:
        List[RecipientResponse]: Lista de destinatarios
    """
    try:
        service = RecipientService(supabase)
        if role:
            result = await service.get_recipients_by_role(role, active_only)
        elif company:
            result = await service.get_recipients_by_company(company, active_only)
        else:
            result = await service.list_recipients(active_only)
        return [RecipientResponse(**r) for r in result]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar destinatarios: {str(e)}"
        )

@router.patch("/{recipient_id}", response_model=RecipientResponse)
async def update_recipient(
    recipient_id: UUID,
    updates: RecipientUpdate,
    supabase = Depends(get_supabase_client)
) -> RecipientResponse:
    """
    Actualiza un destinatario.
    
    Args:
        recipient_id: ID del destinatario
        updates: Datos a actualizar
        supabase: Cliente Supabase (inyectado)
        
    Returns:
        RecipientResponse: Destinatario actualizado
        
    Raises:
        HTTPException: Si hay error en la validación o actualización
    """
    try:
        service = RecipientService(supabase)
        # Verificar que existe
        if not await service.get_recipient(recipient_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Destinatario {recipient_id} no encontrado"
            )
        # Actualizar solo campos no nulos
        update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
        result = await service.update_recipient(recipient_id, update_data)
        return RecipientResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar destinatario: {str(e)}"
        )

@router.delete("/{recipient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recipient(
    recipient_id: UUID,
    supabase = Depends(get_supabase_client)
):
    """
    Elimina un destinatario.
    
    Args:
        recipient_id: ID del destinatario
        supabase: Cliente Supabase (inyectado)
        
    Raises:
        HTTPException: Si hay error en la eliminación
    """
    try:
        service = RecipientService(supabase)
        # Verificar que existe
        if not await service.get_recipient(recipient_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Destinatario {recipient_id} no encontrado"
            )
        await service.delete_recipient(recipient_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar destinatario: {str(e)}"
        )

@router.post("/{recipient_id}/deactivate", response_model=RecipientResponse)
async def deactivate_recipient(
    recipient_id: UUID,
    supabase = Depends(get_supabase_client)
) -> RecipientResponse:
    """
    Desactiva un destinatario.
    
    Args:
        recipient_id: ID del destinatario
        supabase: Cliente Supabase (inyectado)
        
    Returns:
        RecipientResponse: Destinatario desactivado
        
    Raises:
        HTTPException: Si hay error en la desactivación
    """
    try:
        service = RecipientService(supabase)
        # Verificar que existe
        if not await service.get_recipient(recipient_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Destinatario {recipient_id} no encontrado"
            )
        result = await service.deactivate_recipient(recipient_id)
        return RecipientResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al desactivar destinatario: {str(e)}"
        )

@router.post("/{recipient_id}/activate", response_model=RecipientResponse)
async def activate_recipient(
    recipient_id: UUID,
    supabase = Depends(get_supabase_client)
) -> RecipientResponse:
    """
    Activa un destinatario.
    
    Args:
        recipient_id: ID del destinatario
        supabase: Cliente Supabase (inyectado)
        
    Returns:
        RecipientResponse: Destinatario activado
        
    Raises:
        HTTPException: Si hay error en la activación
    """
    try:
        service = RecipientService(supabase)
        # Verificar que existe
        if not await service.get_recipient(recipient_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Destinatario {recipient_id} no encontrado"
            )
        result = await service.activate_recipient(recipient_id)
        return RecipientResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al activar destinatario: {str(e)}"
        ) 