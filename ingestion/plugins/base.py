#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🔌 Sensor Plugin Base - Flow-Monitor                      ║
║                         Layer 1: Universal Plugin Layer                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

Clase base abstracta que define el contrato para todos los plugins de sensores.
Cada fuente de datos (HTTP-JSON, MQTT, Modbus, etc.) debe implementar esta interfaz.

Author: Flow-Monitor Team
Project: Flow-Monitor (MVP Semilla Inicia)
"""

from abc import ABC, abstractmethod
from typing import Any

from ingestion.models import NormalizedReading


class SensorPlugin(ABC):
    """
    🔌 Clase base abstracta para plugins de sensores.
    
    Define el contrato que todos los adaptadores de datos deben cumplir
    para integrarse con el sistema Flow-Monitor.
    
    Cada plugin es responsable de:
    1. Validar que el payload recibido sea procesable
    2. Normalizar los datos crudos al formato estándar NormalizedReading
    
    Example:
        >>> class MyCustomPlugin(SensorPlugin):
        ...     @property
        ...     def name(self) -> str:
        ...         return "my-custom-plugin"
        ...     
        ...     def validate(self, raw_data: dict) -> bool:
        ...         return "sensor_id" in raw_data
        ...     
        ...     def normalize_data(self, raw_data: dict) -> NormalizedReading:
        ...         return NormalizedReading(...)
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Identificador único del plugin.
        
        Returns:
            Nombre del plugin (ej: "http-json", "mqtt", "modbus")
        """
        pass
    
    @property
    def version(self) -> str:
        """Versión del plugin."""
        return "1.0.0"
    
    @property
    def description(self) -> str:
        """Descripción del plugin."""
        return "Sensor plugin for Flow-Monitor"
    
    @abstractmethod
    def validate(self, raw_data: Any) -> bool:
        """
        Valida que el payload recibido sea procesable por este plugin.
        
        Args:
            raw_data: Datos crudos recibidos de la fuente
            
        Returns:
            True si el payload es válido y puede ser normalizado,
            False en caso contrario
        """
        pass
    
    @abstractmethod
    def normalize_data(self, raw_data: Any) -> NormalizedReading:
        """
        Transforma datos crudos al formato estándar interno.
        
        Este método recibe el payload en el formato específico de la fuente
        (JSON, bytes de Modbus, mensaje MQTT, etc.) y lo transforma al
        modelo NormalizedReading que la Capa 2 espera.
        
        Args:
            raw_data: Datos crudos de la fuente
            
        Returns:
            NormalizedReading con los datos en formato estándar
            
        Raises:
            ValueError: Si los datos no pueden ser normalizados
        """
        pass
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', version='{self.version}')>"
