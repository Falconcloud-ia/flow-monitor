"""
Motor de Reglas para Intelligence Core.
Evalúa datos de sensores contra umbrales configurables.
"""

from typing import Optional
from .models import SensorData, RiskLevel
from .config import IntelligenceConfig, ThresholdConfig, config as default_config


class RulesEngine:
    """
    🔧 Motor de Reglas - Evaluador de umbrales configurables.
    
    Evalúa valores de sensores contra umbrales definidos para
    determinar el nivel de riesgo actual.
    
    Ejemplo:
        engine = RulesEngine()
        engine.set_threshold("temperature", max_temp=80, warning_temp=60)
        risk = engine.evaluate(sensor_data)
    """
    
    def __init__(self, config: Optional[IntelligenceConfig] = None):
        self.config = config or default_config
        self._custom_thresholds: dict = {}
    
    def set_threshold(
        self,
        sensor_type: str,
        max_temp: Optional[float] = None,
        warning_temp: Optional[float] = None,
        critical_temp: Optional[float] = None,
        **kwargs
    ) -> None:
        """
        Define umbrales personalizados para un tipo de sensor.
        
        Args:
            sensor_type: Tipo de sensor (ej: "temperature", "vibration")
            max_temp: Umbral máximo normal (alias para normal_max)
            warning_temp: Umbral de advertencia
            critical_temp: Umbral crítico
        """
        # Obtener configuración base
        base = self.config.get_threshold(sensor_type)
        
        # Crear nueva configuración con valores personalizados
        self._custom_thresholds[sensor_type.lower()] = ThresholdConfig(
            critical=critical_temp if critical_temp is not None else base.critical,
            warning=warning_temp if warning_temp is not None else base.warning,
            normal_max=max_temp if max_temp is not None else base.normal_max,
            normal_min=kwargs.get("min_temp", base.normal_min),
            unit=base.unit
        )
    
    def get_threshold(self, sensor_type: str) -> ThresholdConfig:
        """Obtiene los umbrales para un tipo de sensor."""
        sensor_type_lower = sensor_type.lower()
        
        # Primero buscar en umbrales personalizados
        if sensor_type_lower in self._custom_thresholds:
            return self._custom_thresholds[sensor_type_lower]
        
        # Luego en configuración por defecto
        return self.config.get_threshold(sensor_type)
    
    def _infer_sensor_type(self, sensor_data: SensorData) -> str:
        """Infiere el tipo de sensor basado en ID, unidad o ubicación."""
        sensor_id_lower = sensor_data.sensor_id.lower()
        unit_lower = sensor_data.unit.lower()
        
        # Mapeo de identificadores comunes
        type_hints = {
            "temperature": ["temp", "celsius", "fahrenheit", "°c", "°f"],
            "vibration": ["vib", "vibration", "mm/s", "accel"],
            "pressure": ["press", "psi", "bar", "pa"],
            "flow": ["flow", "caudal", "l/min", "gpm"]
        }
        
        for sensor_type, hints in type_hints.items():
            for hint in hints:
                if hint in sensor_id_lower or hint in unit_lower:
                    return sensor_type
        
        # Default a temperatura
        return "temperature"
    
    def evaluate(self, sensor_data: SensorData) -> RiskLevel:
        """
        Evalúa los datos del sensor y determina el nivel de riesgo.
        
        Args:
            sensor_data: Datos normalizados del sensor
            
        Returns:
            RiskLevel indicando el nivel de riesgo actual
        """
        sensor_type = self._infer_sensor_type(sensor_data)
        threshold = self.get_threshold(sensor_type)
        value = sensor_data.value
        
        # Evaluar contra umbrales (orden de prioridad: crítico > warning > normal)
        if value >= threshold.critical:
            return RiskLevel.CRITICAL
        elif value >= threshold.warning:
            return RiskLevel.HIGH
        elif value >= threshold.normal_max:
            return RiskLevel.MEDIUM
        elif value < threshold.normal_min:
            # Valor anormalmente bajo también puede ser problema
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def get_threshold_status(self, sensor_data: SensorData) -> dict:
        """
        Retorna información detallada sobre el estado respecto a umbrales.
        
        Returns:
            Diccionario con distancias a cada umbral
        """
        sensor_type = self._infer_sensor_type(sensor_data)
        threshold = self.get_threshold(sensor_type)
        value = sensor_data.value
        
        return {
            "sensor_type": sensor_type,
            "current_value": value,
            "thresholds": {
                "critical": threshold.critical,
                "warning": threshold.warning,
                "normal_max": threshold.normal_max,
                "normal_min": threshold.normal_min
            },
            "distances": {
                "to_critical": threshold.critical - value,
                "to_warning": threshold.warning - value,
                "to_normal_max": threshold.normal_max - value
            },
            "percentage_to_critical": min(100, (value / threshold.critical) * 100)
        }
