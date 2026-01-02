#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  🌐 HTTP-JSON Plugin - Flow-Monitor                          ║
║                    Layer 1: DataPulse Adapter                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

Plugin concreto para recibir datos del DataPulse Agent via HTTP/JSON.
Normaliza el payload JSON al formato estándar NormalizedReading.

Author: Flow-Monitor Team
Project: Flow-Monitor (MVP Semilla Inicia)
"""

from datetime import datetime
from typing import Any

from ingestion.plugins.base import SensorPlugin
from ingestion.models import NormalizedReading, ReadingType


class HttpJsonPlugin(SensorPlugin):
    """
    🌐 Plugin para ingesta de datos JSON via HTTP.
    
    Este plugin está diseñado para recibir el payload del DataPulse Agent
    y normalizarlo al formato estándar de Flow-Monitor.
    
    Payload esperado del DataPulse:
        {
            "sensor_id": "SENSOR_TEMP_01",
            "timestamp": "2025-12-18T00:53:11",
            "value": 35.5,
            "unit": "Celsius",
            "location": "Planta-A/Horno-Principal",
            "_meta": {
                "status": "NORMAL",
                "is_anomaly": false,
                "step": 42,
                "agent": "DataPulse"
            }
        }
    
    Example:
        >>> plugin = HttpJsonPlugin()
        >>> raw_data = {"sensor_id": "S01", "timestamp": "...", "value": 25.0, "unit": "C"}
        >>> if plugin.validate(raw_data):
        ...     reading = plugin.normalize_data(raw_data)
    """
    
    # Campos requeridos en el payload
    REQUIRED_FIELDS = {"sensor_id", "timestamp", "value", "unit"}
    
    @property
    def name(self) -> str:
        return "http-json-plugin"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "HTTP/JSON adapter for DataPulse sensor data"
    
    def validate(self, raw_data: Any) -> bool:
        """
        Valida que el payload JSON contenga los campos requeridos.
        
        Args:
            raw_data: Diccionario JSON del payload
            
        Returns:
            True si contiene sensor_id, timestamp, value y unit
        """
        if not isinstance(raw_data, dict):
            return False
        
        # Verificar campos requeridos
        for field in self.REQUIRED_FIELDS:
            if field not in raw_data:
                return False
        
        # Verificar que value sea numérico
        if not isinstance(raw_data.get("value"), (int, float)):
            return False
        
        return True
    
    def normalize_data(self, raw_data: dict) -> NormalizedReading:
        """
        Transforma el payload JSON del DataPulse al formato normalizado.
        
        Args:
            raw_data: Diccionario con los datos del sensor
            
        Returns:
            NormalizedReading con los datos estandarizados
            
        Raises:
            ValueError: Si los datos no pueden ser normalizados
        """
        if not self.validate(raw_data):
            raise ValueError(
                f"Invalid payload: missing required fields {self.REQUIRED_FIELDS}"
            )
        
        # Parse timestamp
        timestamp = raw_data["timestamp"]
        if isinstance(timestamp, str):
            # Soportar formato ISO con o sin microsegundos
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        
        # Extraer metadata del campo _meta si existe
        meta = raw_data.get("_meta", {})
        
        # Determinar el tipo de lectura basado en la unidad
        reading_type = self._infer_reading_type(raw_data.get("unit", ""))
        
        # Construir metadata enriquecida
        metadata = {
            "raw_status": meta.get("status"),
            "is_anomaly": meta.get("is_anomaly", False),
            "step": meta.get("step"),
            "agent": meta.get("agent"),
            # Preservar cualquier campo adicional del payload original
            **{k: v for k, v in raw_data.items() 
               if k not in self.REQUIRED_FIELDS | {"location", "_meta"}}
        }
        
        # Limpiar None values
        metadata = {k: v for k, v in metadata.items() if v is not None}
        
        return NormalizedReading(
            sensor_id=raw_data["sensor_id"],
            timestamp=timestamp,
            value=float(raw_data["value"]),
            unit=raw_data["unit"],
            source=self.name,
            location=raw_data.get("location"),
            reading_type=reading_type,
            metadata=metadata,
        )
    
    def _infer_reading_type(self, unit: str) -> ReadingType:
        """
        Infiere el tipo de lectura basado en la unidad de medida.
        
        Args:
            unit: Unidad de medida (ej: "Celsius", "Hz")
            
        Returns:
            ReadingType correspondiente
        """
        unit_lower = unit.lower()
        
        if unit_lower in ("celsius", "fahrenheit", "kelvin", "°c", "°f"):
            return ReadingType.TEMPERATURE
        elif unit_lower in ("hz", "g", "mm/s"):
            return ReadingType.VIBRATION
        elif unit_lower in ("l/min", "gpm", "m³/h"):
            return ReadingType.FLOW
        elif unit_lower in ("bar", "psi", "kpa", "pa"):
            return ReadingType.PRESSURE
        elif unit_lower in ("%rh", "%", "humidity"):
            return ReadingType.HUMIDITY
        
        return ReadingType.GENERIC
