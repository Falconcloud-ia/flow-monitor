"""
Configuración centralizada para Intelligence Core.
Define umbrales y parámetros configurables por tipo de sensor.
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class ThresholdConfig:
    """Configuración de umbrales para un tipo de sensor."""
    critical: float
    warning: float
    normal_max: float
    normal_min: float = 0.0
    unit: str = ""


# Umbrales por defecto para diferentes tipos de sensores
DEFAULT_THRESHOLDS: Dict[str, ThresholdConfig] = {
    "temperature": ThresholdConfig(
        critical=90.0,
        warning=80.0,
        normal_max=60.0,
        normal_min=10.0,
        unit="Celsius"
    ),
    "vibration": ThresholdConfig(
        critical=15.0,
        warning=10.0,
        normal_max=5.0,
        normal_min=0.0,
        unit="mm/s"
    ),
    "pressure": ThresholdConfig(
        critical=150.0,
        warning=120.0,
        normal_max=100.0,
        normal_min=20.0,
        unit="PSI"
    ),
    "flow": ThresholdConfig(
        critical=500.0,
        warning=400.0,
        normal_max=300.0,
        normal_min=50.0,
        unit="L/min"
    ),
}


@dataclass 
class PredictionConfig:
    """Configuración para el modelo predictivo."""
    alert_threshold: float = 0.6  # Probabilidad mínima para generar alerta
    high_risk_threshold: float = 0.8  # Probabilidad para riesgo alto
    trend_weight: float = 0.3  # Peso de la tendencia en el cálculo
    proximity_weight: float = 0.7  # Peso de proximidad a umbrales


@dataclass
class IntelligenceConfig:
    """Configuración completa del Intelligence Core."""
    thresholds: Dict[str, ThresholdConfig] = field(default_factory=lambda: DEFAULT_THRESHOLDS.copy())
    prediction: PredictionConfig = field(default_factory=PredictionConfig)
    
    def get_threshold(self, sensor_type: str) -> ThresholdConfig:
        """Obtiene los umbrales para un tipo de sensor."""
        # Normalizar el tipo de sensor
        sensor_type_lower = sensor_type.lower()
        
        # Buscar coincidencia parcial
        for key, config in self.thresholds.items():
            if key in sensor_type_lower or sensor_type_lower in key:
                return config
        
        # Default a temperatura si no se encuentra
        return self.thresholds.get("temperature", DEFAULT_THRESHOLDS["temperature"])


# Instancia global de configuración (puede ser sobrescrita)
config = IntelligenceConfig()
