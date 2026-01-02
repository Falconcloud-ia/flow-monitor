#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                🔗 Flow-Monitor Live Pipeline Demo                            ║
║                    Sensor → Layer 1 → Layer 2 → Layer 3                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

Script que integra las 3 capas en tiempo real.
Genera datos del sensor y los procesa a través de todo el pipeline,
enviando los resultados al Dashboard en tiempo real.

Usage:
    python run_live_demo.py
    
    (Asegúrate de tener el backend en puerto 8001 y el dashboard corriendo)
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
from sensors.datapulse_sensor import DataPulseAgent, SensorConfig


class LivePipeline:
    """
    🔗 Pipeline en vivo que conecta el sensor con todas las capas.
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
        
        # URL del dashboard backend (Capa 3)
        self.dashboard_url = "http://localhost:8001/api/dashboard/process"
        
        # Estadísticas
        self._processed = 0
        self._errors = 0
        self._start_time = datetime.now()
    
    def process_and_forward(self, sensor_data: dict) -> bool:
        """
        Procesa datos del sensor a través de Capa 2 y los envía a Capa 3.
        
        Args:
            sensor_data: Datos crudos del sensor
            
        Returns:
            True si se procesó y envió correctamente
        """
        try:
            # Paso 1: Procesar con Intelligence Core (Capa 2)
            enriched = self.intelligence.process(sensor_data)
            enriched_dict = enriched.to_dict()
            
            # Paso 2: Preparar payload para Capa 3
            payload = {
                "data_original": enriched_dict["data_original"],
                "risk_level": enriched_dict["risk_level"],
                "prediction_alert": enriched_dict["prediction_alert"],
                "processed_at": enriched_dict.get("processed_at", datetime.now().isoformat())
            }
            
            # Paso 3: Enviar a Dashboard Backend (Capa 3)
            response = requests.post(
                self.dashboard_url,
                json=payload,
                timeout=5
            )
            
            self._processed += 1
            
            # Mostrar resultado
            risk_emoji = {
                "LOW": "🟢",
                "MEDIUM": "🟡", 
                "HIGH": "🟠",
                "CRITICAL": "🔴"
            }.get(enriched_dict["risk_level"], "⚪")
            
            print(f"   └─> {risk_emoji} Capa 2: {enriched_dict['risk_level']} | "
                  f"Prob. Fallo: {enriched_dict['prediction_alert']['failure_probability']:.1%} | "
                  f"API: {response.status_code}")
            
            return response.status_code == 200
            
        except requests.RequestException as e:
            self._errors += 1
            print(f"   └─> ❌ Error enviando a Dashboard: {e}")
            return False
        except Exception as e:
            self._errors += 1
            print(f"   └─> ❌ Error procesando: {e}")
            return False
    
    def get_stats(self) -> dict:
        """Obtiene estadísticas del pipeline."""
        runtime = (datetime.now() - self._start_time).total_seconds()
        return {
            "processed": self._processed,
            "errors": self._errors,
            "runtime_seconds": runtime,
            "processing_rate": self._processed / runtime if runtime > 0 else 0
        }


def main():
    """Ejecuta la demo en vivo del pipeline completo."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                🔗 Flow-Monitor Live Pipeline Demo                             ║
║                    Sensor → Layer 2 → Dashboard (Layer 3)                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Verificar que el dashboard está corriendo
    try:
        health = requests.get("http://localhost:8001/health", timeout=3)
        if health.status_code == 200:
            print("✅ Dashboard Backend (Capa 3) detectado en puerto 8001")
        else:
            print("⚠️  Dashboard Backend respondió con código:", health.status_code)
    except requests.RequestException:
        print("❌ No se pudo conectar al Dashboard Backend en puerto 8001")
        print("   Ejecuta primero: python -m action_layer.api")
        return
    
    # Crear pipeline
    pipeline = LivePipeline()
    
    # Configurar sensor
    config = SensorConfig(
        sensor_id="SENSOR_TEMP_01",
        location="Planta-A/Horno-Principal",
        interval_seconds=1.5,
        send_to_api=False,  # No enviar directamente, nosotros manejamos
        auto_anomaly_probability=0.08  # 8% de anomalías
    )
    
    sensor = DataPulseAgent(config)
    
    # Registrar callback que procesa a través del pipeline
    sensor.register_callback(pipeline.process_and_forward)
    
    print("📡 Sensor DataPulse configurado")
    print("🔄 Intervalo de lecturas: 1.5s")
    print("📊 Probabilidad de anomalías: 8%")
    print("─" * 70)
    print("\n🚀 Iniciando pipeline en vivo...\n")
    print("   Abre el Dashboard en: http://localhost:5173")
    print("   API Docs en: http://localhost:8001/docs")
    print("─" * 70)
    print("\n📥 Lecturas en tiempo real:\n")
    
    try:
        # Ejecutar sensor (bloqueante)
        sensor.run()
    except KeyboardInterrupt:
        sensor.stop()
        print("\n" + "─" * 70)
        stats = pipeline.get_stats()
        print(f"""
📊 ESTADÍSTICAS DEL PIPELINE

   Lecturas procesadas: {stats['processed']}
   Errores: {stats['errors']}
   Tiempo de ejecución: {stats['runtime_seconds']:.1f}s
   Tasa de procesamiento: {stats['processing_rate']:.2f} lecturas/s
""")
        print("─" * 70)
        print("👋 Demo finalizada.\n")


if __name__ == "__main__":
    main()
