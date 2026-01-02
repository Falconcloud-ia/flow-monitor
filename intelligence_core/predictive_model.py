"""
Modelo Predictivo (Mock) para Intelligence Core.
Simula predicciones de fallo basadas en valores actuales y tendencias.
"""

import random
import math
from typing import Optional, List
from collections import deque
from datetime import datetime

from .models import SensorData, PredictionAlert, RiskLevel
from .config import IntelligenceConfig, config as default_config


class PredictiveModel:
    """
    🤖 Modelo Predictivo Mock - Simulador de IA para predicción de fallos.
    
    Calcula probabilidad de fallo futuro basándose en:
    - Proximidad del valor actual a umbrales críticos
    - Tendencia histórica (si está disponible)
    - Factor aleatorio para simular incertidumbre del modelo
    
    Ejemplo:
        model = PredictiveModel()
        alert = model.predict(sensor_data, risk_level)
        print(f"Probabilidad de fallo: {alert.failure_probability:.1%}")
    """
    
    # Mensajes de alerta por tipo de escenario
    ALERT_MESSAGES = {
        "overheat": "⚠️ Alta probabilidad de sobrecalentamiento en próximos 5 minutos",
        "critical_imminent": "🔴 ALERTA: Fallo crítico inminente detectado",
        "trend_warning": "📈 Tendencia ascendente detectada - monitorear de cerca",
        "unstable": "⚡ Comportamiento inestable detectado en el sensor",
        "anomaly": "🔍 Patrón anómalo identificado por el modelo"
    }
    
    RECOMMENDED_ACTIONS = {
        "overheat": "Verificar sistema de enfriamiento inmediatamente",
        "critical_imminent": "Detener operación y realizar inspección de emergencia",
        "trend_warning": "Programar mantenimiento preventivo en las próximas 24h",
        "unstable": "Revisar calibración del sensor y conexiones",
        "anomaly": "Investigar causa raíz de la anomalía"
    }
    
    def __init__(self, config: Optional[IntelligenceConfig] = None):
        self.config = config or default_config
        self._history: deque = deque(maxlen=50)  # Últimas 50 lecturas
        self._prediction_count = 0
    
    def _calculate_proximity_factor(
        self, 
        value: float, 
        threshold_critical: float,
        threshold_warning: float
    ) -> float:
        """
        Calcula factor de proximidad a umbrales críticos.
        Más cerca del umbral = mayor probabilidad.
        
        Returns:
            Factor entre 0.0 y 1.0
        """
        if value >= threshold_critical:
            return 1.0
        elif value >= threshold_warning:
            # Interpolación lineal entre warning y critical
            range_size = threshold_critical - threshold_warning
            distance = value - threshold_warning
            return 0.5 + (distance / range_size) * 0.5
        else:
            # Por debajo de warning
            if threshold_warning > 0:
                ratio = value / threshold_warning
                return max(0, min(0.5, ratio * 0.5))
            return 0.1
    
    def _calculate_trend_factor(self) -> float:
        """
        Calcula factor de tendencia basado en historial.
        Tendencia ascendente = mayor probabilidad.
        
        Returns:
            Factor entre -0.2 y 0.3 (puede reducir o aumentar probabilidad)
        """
        if len(self._history) < 3:
            return 0.0
        
        # Tomar últimas lecturas
        recent = list(self._history)[-10:]
        
        if len(recent) < 3:
            return 0.0
        
        # Calcular pendiente simple
        first_half = sum(recent[:len(recent)//2]) / (len(recent)//2)
        second_half = sum(recent[len(recent)//2:]) / (len(recent) - len(recent)//2)
        
        trend = second_half - first_half
        
        # Normalizar tendencia a factor
        if trend > 5:  # Tendencia ascendente fuerte
            return 0.3
        elif trend > 2:  # Tendencia ascendente moderada
            return 0.15
        elif trend > 0:  # Tendencia ascendente leve
            return 0.05
        elif trend < -5:  # Tendencia descendente fuerte (bueno)
            return -0.2
        elif trend < 0:  # Tendencia descendente
            return -0.1
        
        return 0.0
    
    def _add_noise(self, probability: float) -> float:
        """Añade ruido gaussiano para simular incertidumbre del modelo."""
        noise = random.gauss(0, 0.05)  # ±5% de variación
        return max(0.0, min(1.0, probability + noise))
    
    def _determine_alert_type(
        self, 
        probability: float, 
        risk_level: RiskLevel,
        trend_factor: float
    ) -> Optional[str]:
        """Determina el tipo de alerta a generar."""
        if probability >= 0.9:
            return "critical_imminent"
        elif probability >= 0.7 and risk_level == RiskLevel.CRITICAL:
            return "overheat"
        elif probability >= 0.6 and trend_factor > 0.1:
            return "trend_warning"
        elif risk_level == RiskLevel.HIGH and probability >= 0.5:
            return "unstable"
        elif probability >= 0.5:
            return "anomaly"
        
        return None
    
    def predict(
        self, 
        sensor_data: SensorData, 
        risk_level: RiskLevel,
        threshold_critical: float = 90.0,
        threshold_warning: float = 80.0
    ) -> PredictionAlert:
        """
        Genera una predicción de fallo basada en los datos actuales.
        
        Args:
            sensor_data: Datos del sensor
            risk_level: Nivel de riesgo actual (del RulesEngine)
            threshold_critical: Umbral crítico para cálculos
            threshold_warning: Umbral de advertencia
            
        Returns:
            PredictionAlert con probabilidad y alertas
        """
        self._prediction_count += 1
        value = sensor_data.value
        
        # Añadir al historial
        self._history.append(value)
        
        # Calcular factores
        proximity = self._calculate_proximity_factor(
            value, threshold_critical, threshold_warning
        )
        trend = self._calculate_trend_factor()
        
        # Combinar factores según configuración
        pred_config = self.config.prediction
        base_probability = (
            proximity * pred_config.proximity_weight +
            max(0, trend) * pred_config.trend_weight
        )
        
        # Añadir bonus por nivel de riesgo actual
        risk_bonus = {
            RiskLevel.LOW: 0.0,
            RiskLevel.MEDIUM: 0.1,
            RiskLevel.HIGH: 0.2,
            RiskLevel.CRITICAL: 0.3
        }.get(risk_level, 0.0)
        
        probability = base_probability + risk_bonus
        probability = self._add_noise(probability)
        probability = max(0.0, min(1.0, probability))
        
        # Determinar si generar alerta
        alert_type = self._determine_alert_type(probability, risk_level, trend)
        
        # Calcular confianza del modelo (mock)
        confidence = 0.7 + random.uniform(-0.1, 0.15)
        confidence = min(0.95, max(0.5, confidence))
        
        # Construir respuesta
        alert = PredictionAlert(
            failure_probability=probability,
            confidence=confidence
        )
        
        if alert_type and probability >= pred_config.alert_threshold:
            alert.alert_message = self.ALERT_MESSAGES.get(alert_type)
            alert.recommended_action = self.RECOMMENDED_ACTIONS.get(alert_type)
            
            # Estimar tiempo hasta fallo (mock)
            if probability >= 0.8:
                alert.predicted_time_to_failure = "< 5 minutos"
            elif probability >= 0.6:
                alert.predicted_time_to_failure = "5-15 minutos"
            elif probability >= 0.4:
                alert.predicted_time_to_failure = "15-30 minutos"
        
        return alert
    
    def reset_history(self) -> None:
        """Limpia el historial de lecturas."""
        self._history.clear()
    
    def get_stats(self) -> dict:
        """Retorna estadísticas del modelo."""
        return {
            "predictions_made": self._prediction_count,
            "history_size": len(self._history),
            "average_value": sum(self._history) / len(self._history) if self._history else 0,
            "max_value": max(self._history) if self._history else 0,
            "min_value": min(self._history) if self._history else 0
        }
