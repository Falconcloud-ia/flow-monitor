"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🧠 Intelligence Core - Layer 2 🧠                          ║
║                   Data Analysis & AI for Flow-Monitor                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

Capa de lógica de negocio e inteligencia artificial.
Recibe datos normalizados de sensores (Capa 1) y los enriquece con
evaluación de riesgos y predicciones.

Módulos:
- models: Dataclasses para datos de entrada/salida
- rules_engine: Motor de reglas configurable
- predictive_model: Modelo predictivo (mock)
- intelligence_service: Servicio orquestador principal
"""

from .models import SensorData, RiskLevel, PredictionAlert, EnrichedData
from .rules_engine import RulesEngine
from .predictive_model import PredictiveModel
from .intelligence_service import IntelligenceService

__all__ = [
    "SensorData",
    "RiskLevel", 
    "PredictionAlert",
    "EnrichedData",
    "RulesEngine",
    "PredictiveModel",
    "IntelligenceService",
]

__version__ = "1.0.0"
__author__ = "Intelligence Core Agent"
