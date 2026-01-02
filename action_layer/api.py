#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🎯 Action Layer API - Flow-Monitor                        ║
║                      Layer 3: Dashboard & Notifications                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

API FastAPI para:
- Recibir datos enriquecidos de Capa 2
- Servir datos al Dashboard React via REST y SSE
- Gestionar alertas y notificaciones

Usage:
    python -m action_layer.api
    
    o con uvicorn:
    uvicorn action_layer.api:app --reload --port 8001

Author: Flow-Monitor Team
Project: Flow-Monitor (MVP Semilla Inicia)
"""

import logging
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .data_observer import DataObserver, get_observer
from .notification_dispatcher import NotificationDispatcher
from .models import DashboardReading, AlertNotification


# ═══════════════════════════════════════════════════════════════════════════════
# Configuración de Logging
# ═══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("action_layer.api")


# ═══════════════════════════════════════════════════════════════════════════════
# FastAPI App
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="🎯 Flow-Monitor Action Layer API",
    description="Layer 3 - Dashboard & Notifications for real-time monitoring",
    version="1.0.0",
)

# CORS para desarrollo - permite conexión desde React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar origen del dashboard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# Pydantic Models
# ═══════════════════════════════════════════════════════════════════════════════

class EnrichedDataInput(BaseModel):
    """Datos enriquecidos recibidos de Capa 2."""
    data_original: Dict[str, Any]
    risk_level: str
    prediction_alert: Dict[str, Any]
    processed_at: Optional[str] = None


class ProcessResponse(BaseModel):
    """Respuesta al procesar datos."""
    success: bool
    reading_id: str
    risk_level: str
    notification_sent: bool
    timestamp: str


class DashboardDataResponse(BaseModel):
    """Estructura completa de datos para Dashboard."""
    readings: List[Dict[str, Any]]
    alerts: List[Dict[str, Any]]
    stats: Dict[str, Any]


class HealthResponse(BaseModel):
    """Respuesta del health check."""
    status: str
    layer: str
    timestamp: str
    stats: Dict[str, Any]


# ═══════════════════════════════════════════════════════════════════════════════
# Instancias Globales
# ═══════════════════════════════════════════════════════════════════════════════

# Usamos la instancia singleton del observer
observer = get_observer()


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoints - Health & Info
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["Health"])
async def root():
    """Endpoint raíz con información de la API."""
    return {
        "service": "Flow-Monitor Action Layer API",
        "layer": "3 - Dashboard & Notifications",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "dashboard": "/api/dashboard/data",
            "stream": "/api/dashboard/stream",
            "process": "/api/dashboard/process"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Verifica el estado del servicio."""
    return HealthResponse(
        status="healthy",
        layer="3 - Action Layer",
        timestamp=datetime.now().isoformat(),
        stats=observer.get_stats()
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoints - Dashboard Data
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/dashboard/data", response_model=DashboardDataResponse, tags=["Dashboard"])
async def get_dashboard_data(
    readings_limit: int = Query(100, ge=1, le=500, description="Límite de lecturas"),
    alerts_limit: int = Query(20, ge=1, le=100, description="Límite de alertas")
):
    """
    📊 Obtiene datos completos para el Dashboard.
    
    Retorna:
    - readings: Últimas lecturas de sensores (todos los niveles)
    - alerts: Alertas enviadas
    - stats: Estadísticas agregadas
    """
    return DashboardDataResponse(**observer.get_dashboard_data(readings_limit, alerts_limit))


@app.get("/api/dashboard/readings", tags=["Dashboard"])
async def get_readings(
    limit: int = Query(100, ge=1, le=500),
    risk_level: Optional[str] = Query(None, description="Filtrar por nivel de riesgo")
):
    """
    📈 Obtiene lecturas de sensores.
    
    Opcionalmente filtra por nivel de riesgo (LOW, MEDIUM, HIGH, CRITICAL).
    """
    if risk_level:
        if risk_level.upper() not in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid risk_level: {risk_level}. Must be LOW, MEDIUM, HIGH, or CRITICAL"
            )
        return {
            "total": len(observer.get_readings_by_risk(risk_level.upper(), limit)),
            "risk_level": risk_level.upper(),
            "readings": observer.get_readings_by_risk(risk_level.upper(), limit)
        }
    
    return {
        "total": len(observer.get_readings(limit)),
        "readings": observer.get_readings(limit)
    }


@app.get("/api/dashboard/alerts", tags=["Dashboard"])
async def get_alerts(limit: int = Query(50, ge=1, le=200)):
    """
    🔔 Obtiene historial de alertas enviadas.
    """
    alerts = observer.get_alerts(limit)
    return {
        "total": len(alerts),
        "alerts": alerts
    }


@app.get("/api/dashboard/stats", tags=["Dashboard"])
async def get_stats():
    """
    📊 Obtiene estadísticas agregadas.
    """
    return observer.get_stats()


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoints - Data Processing (recibe de Capa 2)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/dashboard/process", response_model=ProcessResponse, tags=["Processing"])
async def process_enriched_data(data: EnrichedDataInput):
    """
    🔄 Recibe y procesa datos enriquecidos de Capa 2.
    
    Este endpoint es llamado por la Capa 2 cuando procesa nuevos datos.
    El sistema:
    1. Transforma los datos a formato Dashboard
    2. Los almacena en buffer
    3. Dispara notificaciones si es necesario
    4. Notifica a clientes SSE conectados
    """
    try:
        # Preparar datos
        enriched_data = {
            "data_original": data.data_original,
            "risk_level": data.risk_level,
            "prediction_alert": data.prediction_alert,
            "processed_at": data.processed_at or datetime.now().isoformat()
        }
        
        # Procesar con el observer
        reading = observer.process(enriched_data)
        
        # Verificar si se envió notificación
        alerts = observer.get_alerts(limit=1)
        notification_sent = len(alerts) > 0 and alerts[-1].get("sensor_id") == reading.sensor_id
        
        logger.info(f"📥 Processed: {reading.risk_emoji} [{reading.sensor_id}] = {reading.value}{reading.unit}")
        
        if reading.risk_level == "CRITICAL":
            logger.warning(f"🔴 CRITICAL ALERT: {reading.sensor_id}")
        
        return ProcessResponse(
            success=True,
            reading_id=reading.id,
            risk_level=reading.risk_level,
            notification_sent=notification_sent,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error processing data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/api/dashboard/process/batch", tags=["Processing"])
async def process_batch(data_list: List[EnrichedDataInput]):
    """
    📦 Procesa un lote de datos enriquecidos.
    """
    results = []
    for data in data_list:
        try:
            enriched_data = {
                "data_original": data.data_original,
                "risk_level": data.risk_level,
                "prediction_alert": data.prediction_alert,
                "processed_at": data.processed_at or datetime.now().isoformat()
            }
            reading = observer.process(enriched_data)
            results.append({
                "success": True,
                "reading_id": reading.id,
                "risk_level": reading.risk_level
            })
        except Exception as e:
            results.append({
                "success": False,
                "error": str(e)
            })
    
    return {
        "processed": len(results),
        "results": results
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoints - Server-Sent Events (SSE) para Real-time
# ═══════════════════════════════════════════════════════════════════════════════

async def event_generator():
    """Generador de eventos SSE."""
    queue = observer.create_event_queue()
    
    try:
        # Enviar evento de conexión
        yield f"event: connected\ndata: {json.dumps({'status': 'connected', 'timestamp': datetime.now().isoformat()})}\n\n"
        
        while True:
            try:
                # Esperar nuevo evento con timeout
                reading = await asyncio.wait_for(queue.get(), timeout=30.0)
                
                # Formatear como SSE
                event_data = json.dumps(reading.to_dict())
                yield f"event: reading\ndata: {event_data}\n\n"
                
            except asyncio.TimeoutError:
                # Enviar heartbeat cada 30 segundos
                yield f"event: heartbeat\ndata: {json.dumps({'timestamp': datetime.now().isoformat()})}\n\n"
                
    except asyncio.CancelledError:
        pass


@app.get("/api/dashboard/stream", tags=["Real-time"])
async def stream_readings():
    """
    📡 Stream de datos en tiempo real via Server-Sent Events (SSE).
    
    Conectarse a este endpoint para recibir actualizaciones en vivo.
    
    Eventos:
    - `connected`: Conexión establecida
    - `reading`: Nueva lectura de sensor
    - `heartbeat`: Keep-alive cada 30 segundos
    
    Ejemplo JavaScript:
    ```js
    const eventSource = new EventSource('/api/dashboard/stream');
    eventSource.addEventListener('reading', (e) => {
        const data = JSON.parse(e.data);
        console.log('Nueva lectura:', data);
    });
    ```
    """
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Endpoints - Admin/Debug
# ═══════════════════════════════════════════════════════════════════════════════

@app.delete("/api/dashboard/clear", tags=["Admin"])
async def clear_data():
    """🗑️ Limpia todos los datos (para testing)."""
    observer.clear()
    return {"message": "Data cleared", "success": True}


# ═══════════════════════════════════════════════════════════════════════════════
# Main Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🎯 Flow-Monitor Action Layer API                          ║
║                      Layer 3: Dashboard & Notifications                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "action_layer.api:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info",
    )
