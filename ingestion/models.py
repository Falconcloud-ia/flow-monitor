#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   📊 Normalized Data Models - Flow-Monitor                    ║
║                       Layer 1: Standard Data Format                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

Modelos de datos normalizados que representan el formato estándar interno.
Todos los plugins deben convertir sus datos a estos modelos.

Author: Flow-Monitor Team
Project: Flow-Monitor (MVP Semilla Inicia)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from enum import Enum


class ReadingType(Enum):
    """Tipos de lecturas soportadas."""
    TEMPERATURE = "temperature"
    VIBRATION = "vibration"
    FLOW = "flow"
    PRESSURE = "pressure"
    HUMIDITY = "humidity"
    GENERIC = "generic"


@dataclass
class NormalizedReading:
    """
    📊 Modelo de datos normalizado para lecturas de sensores.
    
    Este es el formato estándar que la Capa 2 (Intelligence Core) consume.
    Todos los plugins de ingesta deben producir instancias de este modelo.
    
    Attributes:
        sensor_id: Identificador único del sensor
        timestamp: Momento de la lectura (UTC)
        value: Valor numérico de la lectura
        unit: Unidad de medida (ej: "Celsius", "Hz", "L/min")
        source: Nombre del plugin que generó el dato
        location: Ubicación física del sensor (opcional)
        reading_type: Tipo de lectura (temperatura, vibración, etc.)
        metadata: Datos adicionales específicos del sensor
        
    Example:
        >>> reading = NormalizedReading(
        ...     sensor_id="SENSOR_TEMP_01",
        ...     timestamp=datetime.now(),
        ...     value=35.5,
        ...     unit="Celsius",
        ...     source="http-json-plugin"
        ... )
    """
    sensor_id: str
    timestamp: datetime
    value: float
    unit: str
    source: str
    location: Optional[str] = None
    reading_type: ReadingType = ReadingType.GENERIC
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Validación post-inicialización."""
        if not self.sensor_id:
            raise ValueError("sensor_id cannot be empty")
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be a datetime object")
        if not isinstance(self.value, (int, float)):
            raise ValueError("value must be numeric")
    
    def to_dict(self) -> dict:
        """
        Convierte el reading a diccionario para serialización.
        
        Returns:
            Diccionario con todos los campos normalizados
        """
        return {
            "sensor_id": self.sensor_id,
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "unit": self.unit,
            "source": self.source,
            "location": self.location,
            "reading_type": self.reading_type.value,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "NormalizedReading":
        """
        Crea una instancia desde un diccionario.
        
        Args:
            data: Diccionario con los campos del reading
            
        Returns:
            Nueva instancia de NormalizedReading
        """
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        reading_type = data.get("reading_type", "generic")
        if isinstance(reading_type, str):
            reading_type = ReadingType(reading_type)
        
        return cls(
            sensor_id=data["sensor_id"],
            timestamp=timestamp,
            value=float(data["value"]),
            unit=data["unit"],
            source=data["source"],
            location=data.get("location"),
            reading_type=reading_type,
            metadata=data.get("metadata", {}),
        )
    
    def is_critical(self, threshold: float) -> bool:
        """Verifica si el valor supera un umbral crítico."""
        return self.value >= threshold
    
    def __str__(self) -> str:
        return (
            f"[{self.timestamp.strftime('%H:%M:%S')}] "
            f"{self.sensor_id}: {self.value:.2f} {self.unit}"
        )
