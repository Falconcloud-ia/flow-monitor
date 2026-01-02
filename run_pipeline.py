#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                🔗 Flow-Monitor Full Pipeline Integrator                      ║
║                    Demo: Layer 1 → Layer 2 → Layer 3                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

Script que integra las 3 capas del sistema Flow-Monitor para demostración.
Inicia todos los servicios y muestra el flujo completo de datos.

Usage:
    python run_pipeline.py
"""

import sys
import os
import time
import threading
import requests
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intelligence_core import IntelligenceService
from action_layer.data_observer import get_observer
from action_layer.notification_dispatcher import NotificationDispatcher


class FlowMonitorPipeline:
    """
    🔗 Pipeline integrador de las 3 capas.
    
    Flujo:
        DataPulse → Ingestion API (L1) → Intelligence Service (L2) → Action Layer (L3)
    """
    
    def __init__(self):
        # Capa 2: Intelligence Core
        self.intelligence = IntelligenceService()
        self.intelligence.configure_threshold(
            "temperature",
            max_temp=60,
            warning_temp=80,
            critical_temp=90
        )
        
        # Capa 3: Action Layer
        self.observer = get_observer()
        self.dispatcher = NotificationDispatcher(
            whatsapp_recipient="+56912345678",
            email_recipient="operador@flowmonitor.demo"
        )
        
        # Estadísticas
        self._processed = 0
        self._start_time = datetime.now()
    
    def process_sensor_reading(self, raw_data: dict) -> dict:
        """
        Procesa una lectura de sensor a través de todo el pipeline.
        
        Args:
            raw_data: Datos crudos normalizados de Capa 1
            
        Returns:
            Resultado del Dashboard con lectura procesada
        """
        # Paso 1: Normalización (ya viene de Capa 1 en formato estándar)
        # raw_data ya está en formato: {sensor_id, timestamp, value, unit, location}
        
        # Paso 2: Intelligence Core (Capa 2)
        enriched = self.intelligence.process(raw_data)
        enriched_dict = enriched.to_dict()
        
        # Paso 3: Action Layer (Capa 3) - Observer procesa y notifica
        reading = self.observer.process(enriched_dict)
        
        self._processed += 1
        
        return {
            "reading": reading.to_dict(),
            "enriched_data": enriched_dict,
            "pipeline_stats": {
                "total_processed": self._processed,
                "uptime": (datetime.now() - self._start_time).total_seconds()
            }
        }
    
    def get_dashboard_data(self) -> dict:
        """Obtiene datos para el Dashboard."""
        return self.observer.get_dashboard_data()
    
    def get_pipeline_stats(self) -> dict:
        """Obtiene estadísticas del pipeline."""
        return {
            "pipeline": {
                "total_processed": self._processed,
                "uptime_seconds": (datetime.now() - self._start_time).total_seconds()
            },
            "layer2_stats": self.intelligence.get_stats(),
            "layer3_stats": self.observer.get_stats()
        }


def demo_pipeline():
    """Ejecuta una demostración del pipeline completo."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                🔗 Flow-Monitor Full Pipeline Demo                            ║
║                    Layer 1 → Layer 2 → Layer 3                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Crear pipeline
    pipeline = FlowMonitorPipeline()
    
    # Datos de prueba simulando lecturas de DataPulse (Capa 1)
    test_readings = [
        # Lecturas normales (LOW)
        {"sensor_id": "SENSOR_TEMP_01", "timestamp": "2025-12-18T01:00:00", "value": 35.0, "unit": "°C", "location": "Planta-A/Horno-1"},
        {"sensor_id": "SENSOR_TEMP_01", "timestamp": "2025-12-18T01:00:02", "value": 42.0, "unit": "°C", "location": "Planta-A/Horno-1"},
        {"sensor_id": "SENSOR_TEMP_01", "timestamp": "2025-12-18T01:00:04", "value": 55.0, "unit": "°C", "location": "Planta-A/Horno-1"},
        
        # Lecturas elevadas (MEDIUM/HIGH)
        {"sensor_id": "SENSOR_TEMP_01", "timestamp": "2025-12-18T01:00:06", "value": 68.0, "unit": "°C", "location": "Planta-A/Horno-1"},
        {"sensor_id": "SENSOR_TEMP_01", "timestamp": "2025-12-18T01:00:08", "value": 75.0, "unit": "°C", "location": "Planta-A/Horno-1"},
        {"sensor_id": "SENSOR_TEMP_01", "timestamp": "2025-12-18T01:00:10", "value": 82.0, "unit": "°C", "location": "Planta-A/Horno-1"},
        
        # ¡ANOMALÍA! (CRITICAL)
        {"sensor_id": "SENSOR_TEMP_01", "timestamp": "2025-12-18T01:00:12", "value": 95.0, "unit": "°C", "location": "Planta-A/Horno-1", "_meta": {"is_anomaly": True, "anomaly_type": "spike"}},
        
        # Otro sensor también crítico
        {"sensor_id": "SENSOR_TEMP_02", "timestamp": "2025-12-18T01:00:14", "value": 98.0, "unit": "°C", "location": "Planta-B/Motor-3", "_meta": {"is_anomaly": True}},
    ]
    
    print("📊 Procesando lecturas a través del pipeline...\n")
    print("─" * 80)
    
    for i, reading in enumerate(test_readings, 1):
        print(f"\n📥 Lectura #{i}: {reading['sensor_id']} = {reading['value']}{reading['unit']}")
        
        # Procesar a través del pipeline
        result = pipeline.process_sensor_reading(reading)
        
        # Mostrar resultado
        r = result["reading"]
        e = result["enriched_data"]
        
        print(f"   └─ {r['risk_emoji']} Riesgo: {r['risk_level']}")
        print(f"   └─ 🎯 Prob. Fallo: {r['prediction']['failure_probability']:.1%}")
        
        if r['prediction'].get('alert_message'):
            print(f"   └─ ⚠️  {r['prediction']['alert_message']}")
        
        # Pequeña pausa para visualización
        time.sleep(0.3)
    
    print("\n" + "─" * 80)
    
    # Mostrar datos finales del Dashboard
    print("\n📈 DATOS PARA DASHBOARD:\n")
    dashboard = pipeline.get_dashboard_data()
    
    print(f"   📊 Total lecturas: {dashboard['stats']['total_readings']}")
    print(f"   📉 Distribución por riesgo:")
    for level, count in dashboard['stats']['readings_by_risk'].items():
        emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}.get(level, "⚪")
        print(f"      {emoji} {level}: {count}")
    
    print(f"\n   🔔 Alertas enviadas: {dashboard['stats']['alerts_sent']}")
    
    if dashboard['alerts']:
        print(f"\n   📢 Últimas alertas:")
        for alert in dashboard['alerts'][-3:]:
            print(f"      └─ [{alert['channel']}] {alert['sensor_id']}: {alert['risk_level']}")
    
    print("\n" + "═" * 80)
    print("✅ Demo del pipeline completada.")
    print("═" * 80)
    
    # Retornar estructura JSON final
    import json
    print("\n📦 ESTRUCTURA JSON FINAL PARA REACT DASHBOARD:\n")
    print(json.dumps(dashboard, indent=2, ensure_ascii=False))
    
    return dashboard


if __name__ == "__main__":
    demo_pipeline()
