"""
Rutas para la API de cartones CNPJ.
"""
from typing import Optional, Any, Dict, List
from fastapi import APIRouter, HTTPException, Query, Depends, status
from pydantic import BaseModel, Field

from src.services.cnpj_service import CNPJService, CNPJServiceError
from src.dependencies import get_cnpj_service

router = APIRouter(prefix="/api/v1/cnpj", tags=["CNPJ"])

class CNPJCardData(BaseModel):
    """Datos de cartón CNPJ."""
    cnpj: str = Field(..., description="CNPJ consultado")
    storage_path: str = Field(..., description="Ruta en Supabase Storage")
    public_url: str = Field(..., description="URL pública del cartón")
    file_size_bytes: int = Field(..., description="Tamaño del archivo en bytes")
    generated_at: str = Field(..., description="Fecha de generación")
    api_source: str = Field(..., description="Fuente de los datos")

class CNPJCardResponse(BaseModel):
    """Respuesta de cartón CNPJ."""
    success: bool = Field(..., description="Si la operación fue exitosa")
    message: str = Field(..., description="Mensaje descriptivo")
    data: Optional[CNPJCardData] = Field(None, description="Datos del cartón")

class CNPJCardListResponse(BaseModel):
    """Respuesta de lista de cartones CNPJ."""
    success: bool = Field(..., description="Si la operación fue exitosa")
    data: List[CNPJCardData] = Field(..., description="Lista de cartones")
    total: int = Field(..., description="Total de registros")
    limit: int = Field(..., description="Límite de registros por página")
    offset: int = Field(..., description="Desplazamiento de la página")
    has_more: bool = Field(..., description="Si hay más registros")

@router.get("/card/{cnpj}", response_model=CNPJCardResponse)
async def get_cnpj_card(
    cnpj: str,
    force_refresh: bool = False,
    cnpj_service: CNPJService = Depends(get_cnpj_service)
) -> Dict[str, Any]:
    """
    Obtiene o genera un cartón CNPJ.
    
    Args:
        cnpj: CNPJ para consultar
        force_refresh: Si debe forzar regeneración aunque exista
        cnpj_service: Servicio CNPJ (inyectado)
        
    Returns:
        Información del cartón CNPJ
        
    Raises:
        HTTPException: Si hay error al obtener/generar el cartón
    """
    try:
        # Limpiar CNPJ
        cnpj_clean = ''.join(filter(str.isdigit, cnpj))
        
        if len(cnpj_clean) != 14:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CNPJ inválido"
            )
        
        # Obtener o generar cartón
        result = await cnpj_service.generate_cnpj_card(cnpj_clean, force_refresh)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cartón CNPJ no encontrado"
            )
        
        return {
            "success": True,
            "message": "Cartón CNPJ generado con éxito",
            "data": result
        }
        
    except CNPJServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener/generar cartón CNPJ: {str(e)}"
        )

@router.get("/cards", response_model=CNPJCardListResponse)
async def list_cnpj_cards(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    order_by: str = Query("generated_at", pattern="^[a-zA-Z_]+$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    cnpj_service: CNPJService = Depends(get_cnpj_service)
) -> Dict[str, Any]:
    """
    Lista cartones CNPJ almacenados.
    
    Args:
        limit: Límite de resultados por página
        offset: Desplazamiento para paginación
        order_by: Campo para ordenar
        order: Dirección del orden (asc/desc)
        cnpj_service: Servicio CNPJ (inyectado)
        
    Returns:
        Lista paginada de cartones CNPJ
        
    Raises:
        HTTPException: Si hay error al listar cartones
    """
    try:
        result = await cnpj_service.list_cnpj_cards(
            limit=limit,
            offset=offset,
            order_by=order_by,
            order=order
        )
        
        return result
        
    except CNPJServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar cartones CNPJ: {str(e)}"
        ) 