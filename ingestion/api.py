#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🚀 Ingestion API - Flow-Monitor                           ║
║                      Layer 1: HTTP Endpoint                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

API FastAPI para recibir datos de sensores via HTTP.
Este es el punto de entrada de la Capa 1 que recibe datos del DataPulse
y los normaliza para la Capa 2.

Usage:
    python -m ingestion.api
    
    o con uvicorn:
    uvicorn ingestion.api:app --reload --port 8000

Author: Flow-Monitor Team
Project: Flow-Monitor (MVP Semilla Inicia)
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ingestion.models import NormalizedReading
from ingestion.registry import get_default_registry, PluginNotFoundError


# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("ingestion.api")


# ═══════════════════════════════════════════════════════════════════════════════
# FastAPI App
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="🔌 Flow-Monitor Ingestion API",
    description="Layer 1 - Universal Plugin Layer for sensor data ingestion",
    version="1.0.0",
)

# CORS para desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# Pydantic Models
# ═══════════════════════════════════════════════════════════════════════════════

class IngestResponse(BaseModel):
    """Respuesta de la API de ingesta."""
    success: bool
    message: str
    normalized_data: Optional[Dict[str, Any]] = None
    timestamp: str


class HealthResponse(BaseModel):
    """Respuesta del health check."""
    status: str
    timestamp: str
    plugins_loaded: List[str]


# ═══════════════════════════════════════════════════════════════════════════════
# Buffer para Capa 2 (MVP: lista en memoria)
# ═══════════════════════════════════════════════════════════════════════════════

# En producción esto sería una cola (RabbitMQ/Redis)
readings_buffer: List[NormalizedReading] = []
MAX_BUFFER_SIZE = 1000


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["Health"])
async def root():
    """Endpoint raíz con información de la API."""
    return {
        "service": "Flow-Monitor Ingestion API",
        "layer": "1 - Universal Plugin Layer",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Verifica el estado del servicio y plugins cargados."""
    registry = get_default_registry()
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        plugins_loaded=registry.list_plugins(),
    )


@app.post("/api/ingest", response_model=IngestResponse, tags=["Ingestion"])
async def ingest_sensor_data(payload: Dict[str, Any]):
    """
    🔌 Endpoint principal de ingesta de datos de sensores.
    
    Recibe datos en formato JSON del DataPulse Agent o cualquier fuente,
    los valida y normaliza usando el plugin apropiado.
    
    El dato normalizado queda disponible para que la Capa 2 lo consuma.
    
    Args:
        payload: Diccionario JSON con los datos del sensor
        
    Returns:
        IngestResponse con el dato normalizado
    """
    try:
        registry = get_default_registry()
        
        # Por ahora usamos el plugin por defecto (http-json-plugin)
        # En el futuro se podría detectar el plugin basado en headers o payload
        plugin = registry.get("http-json-plugin")
        
        # Validar payload
        if not plugin.validate(payload):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payload: missing required fields (sensor_id, timestamp, value, unit)"
            )
        
        # Normalizar datos
        normalized = plugin.normalize_data(payload)
        
        # Guardar en buffer para Capa 2
        readings_buffer.append(normalized)
        if len(readings_buffer) > MAX_BUFFER_SIZE:
            readings_buffer.pop(0)  # FIFO
        
        # Log para debugging
        logger.info(f"📥 Ingested: {normalized}")
        
        # Detectar anomalías para log especial
        if normalized.metadata.get("is_anomaly"):
            logger.warning(f"🔥 ANOMALY DETECTED: {normalized.sensor_id} = {normalized.value} {normalized.unit}")
        
        return IngestResponse(
            success=True,
            message="Data ingested and normalized successfully",
            normalized_data=normalized.to_dict(),
            timestamp=datetime.now().isoformat(),
        )
        
    except PluginNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/api/buffer", tags=["Debug"])
async def get_buffer(limit: int = 10):
    """
    🔍 Endpoint de debug para ver los últimos readings en el buffer.
    
    Args:
        limit: Número máximo de readings a retornar
        
    Returns:
        Lista de los últimos readings normalizados
    """
    return {
        "total_in_buffer": len(readings_buffer),
        "readings": [r.to_dict() for r in readings_buffer[-limit:]],
    }


@app.delete("/api/buffer", tags=["Debug"])
async def clear_buffer():
    """Limpia el buffer de readings (para testing)."""
    readings_buffer.clear()
    return {"message": "Buffer cleared", "success": True}


@app.get("/api/plugins", tags=["Plugins"])
async def list_plugins():
    """Lista todos los plugins registrados."""
    registry = get_default_registry()
    plugins = registry.get_all()
    
    return {
        "total": len(plugins),
        "plugins": [
            {
                "name": p.name,
                "version": p.version,
                "description": p.description,
            }
            for p in plugins.values()
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Main Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🚀 Flow-Monitor Ingestion API                             ║
║                      Layer 1: Universal Plugin Layer                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "ingestion.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
