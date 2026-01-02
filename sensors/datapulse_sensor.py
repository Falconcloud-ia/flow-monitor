#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         🔥 DataPulse Agent 🔥                                ║
║                   Virtual IoT Sensor for Flow-Monitor                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

Agente responsable de generar datos de sensores en tiempo real.
Simula una onda normal de temperatura y permite inyectar anomalías
para pruebas del sistema Flow-Monitor.

Author: DataPulse Agent
Project: Flow-Monitor (MVP Semilla Inicia)
"""

import requests
import time
import random
import math
import threading
import argparse
from datetime import datetime
from typing import Callable, Optional
from dataclasses import dataclass
from enum import Enum


class SensorStatus(Enum):
    """Estados posibles del sensor."""
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    ANOMALY_INJECTED = "ANOMALY_INJECTED"


@dataclass
class SensorConfig:
    """Configuración del sensor virtual."""
    sensor_id: str = "SENSOR_TEMP_01"
    location: str = "Planta-A/Horno-Principal"
    unit: str = "Celsius"
    
    # Configuración de la onda normal (20-40°C según project_context)
    base_temp: float = 30.0  # Centro de la onda
    amplitude: float = 10.0  # Variación (30 ± 10 = 20-40°C)
    noise_range: float = 2.0  # Ruido aleatorio
    wave_period: float = 50.0  # Período de la onda senoidal
    
    # Umbrales de alerta
    warning_threshold: float = 60.0
    critical_threshold: float = 80.0
    
    # Configuración de anomalías
    anomaly_min: float = 85.0
    anomaly_max: float = 110.0
    auto_anomaly_probability: float = 0.05  # 5% probabilidad automática
    
    # Conexión
    api_endpoint: str = "http://localhost:8000/api/ingest"
    interval_seconds: float = 2.0
    send_to_api: bool = False  # Solo simulación por defecto


class DataPulseAgent:
    """
    🤖 DataPulse Agent - Generador de datos de sensores IoT virtuales.
    
    Simula un sensor industrial que genera lecturas de temperatura
    siguiendo una onda senoidal con ruido, y permite inyectar anomalías
    tanto manualmente como automáticamente.
    """
    
    def __init__(self, config: Optional[SensorConfig] = None):
        self.config = config or SensorConfig()
        self.step = 0
        self.running = False
        self.manual_anomaly_active = False
        self.anomaly_duration = 0
        self._thread: Optional[threading.Thread] = None
        self._callbacks: list[Callable] = []
        
        # Estadísticas
        self.total_readings = 0
        self.total_anomalies = 0
        self.start_time: Optional[datetime] = None

    def _generate_normal_wave(self) -> float:
        """
        Genera un valor de temperatura basado en una onda senoidal.
        Simula el comportamiento natural de un horno industrial.
        
        Returns:
            Temperatura en el rango configurado (por defecto 20-40°C)
        """
        # Onda senoidal base
        wave_value = math.sin(self.step / self.config.wave_period * 2 * math.pi)
        temperature = self.config.base_temp + (self.config.amplitude * wave_value)
        
        # Añadir ruido gaussiano para mayor realismo
        noise = random.gauss(0, self.config.noise_range / 2)
        
        return temperature + noise

    def _generate_anomaly(self) -> float:
        """
        Genera un valor de temperatura anómalo (pico crítico).
        Simula un fallo en el sistema de refrigeración o sobrecalentamiento.
        
        Returns:
            Temperatura anómala (por defecto 85-110°C)
        """
        # Pico drástico con algo de variación
        base_anomaly = random.uniform(self.config.anomaly_min, self.config.anomaly_max)
        # Añadir oscilación para simular inestabilidad
        oscillation = random.uniform(-5, 5)
        return base_anomaly + oscillation

    def _determine_status(self, temperature: float, is_anomaly: bool) -> SensorStatus:
        """Determina el estado del sensor basado en la temperatura."""
        if is_anomaly:
            return SensorStatus.ANOMALY_INJECTED
        elif temperature >= self.config.critical_threshold:
            return SensorStatus.CRITICAL
        elif temperature >= self.config.warning_threshold:
            return SensorStatus.WARNING
        return SensorStatus.NORMAL

    def inject_anomaly(self, duration: int = 1):
        """
        Inyecta una anomalía manual por un número específico de lecturas.
        
        Args:
            duration: Número de lecturas que durará la anomalía
        """
        self.manual_anomaly_active = True
        self.anomaly_duration = duration
        print(f"\n🔥 [DataPulse] ANOMALÍA INYECTADA - Durará {duration} lectura(s)\n")

    def stop_anomaly(self):
        """Detiene una anomalía manual activa."""
        self.manual_anomaly_active = False
        self.anomaly_duration = 0
        print("\n✅ [DataPulse] Anomalía detenida manualmente\n")

    def generate_reading(self) -> dict:
        """
        Genera una lectura completa del sensor.
        
        Returns:
            Diccionario con la estructura esperada por Flow-Monitor
        """
        is_anomaly = False
        
        # Verificar si hay anomalía manual activa
        if self.manual_anomaly_active and self.anomaly_duration > 0:
            temperature = self._generate_anomaly()
            is_anomaly = True
            self.anomaly_duration -= 1
            if self.anomaly_duration <= 0:
                self.manual_anomaly_active = False
        # Verificar probabilidad de anomalía automática
        elif random.random() < self.config.auto_anomaly_probability:
            temperature = self._generate_anomaly()
            is_anomaly = True
        else:
            temperature = self._generate_normal_wave()
        
        status = self._determine_status(temperature, is_anomaly)
        
        if is_anomaly:
            self.total_anomalies += 1
        
        self.total_readings += 1
        self.step += 1
        
        # Estructura JSON según project_context.md
        payload = {
            "sensor_id": self.config.sensor_id,
            "timestamp": datetime.now().isoformat(),
            "value": round(temperature, 2),
            "unit": self.config.unit,
            "location": self.config.location,
            # Campos adicionales para debugging
            "_meta": {
                "status": status.value,
                "is_anomaly": is_anomaly,
                "step": self.step,
                "agent": "DataPulse"
            }
        }
        
        return payload

    def _send_to_api(self, payload: dict) -> Optional[int]:
        """Envía los datos al endpoint configurado."""
        if not self.config.send_to_api:
            return None
        
        try:
            response = requests.post(
                self.config.api_endpoint,
                json=payload,
                timeout=5
            )
            return response.status_code
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Error enviando datos: {e}")
            return None

    def _format_output(self, payload: dict) -> str:
        """Formatea la salida para la consola."""
        status = payload["_meta"]["status"]
        temp = payload["value"]
        timestamp = payload["timestamp"].split("T")[1][:8]
        
        # Colores según estado
        if status == "ANOMALY_INJECTED" or status == "CRITICAL":
            indicator = "🔴"
            status_color = "\033[91m"  # Rojo
        elif status == "WARNING":
            indicator = "🟡"
            status_color = "\033[93m"  # Amarillo
        else:
            indicator = "🟢"
            status_color = "\033[92m"  # Verde
        
        reset = "\033[0m"
        
        return (
            f"{indicator} [{timestamp}] "
            f"{status_color}{temp:6.2f}°C{reset} | "
            f"Estado: {status_color}{status:18}{reset} | "
            f"Sensor: {payload['sensor_id']}"
        )

    def run_once(self) -> dict:
        """Ejecuta una sola lectura y retorna el payload."""
        payload = self.generate_reading()
        status_code = self._send_to_api(payload)
        
        print(self._format_output(payload))
        
        if status_code:
            print(f"   └─> API Response: {status_code}")
        
        # Notificar a callbacks registrados
        for callback in self._callbacks:
            callback(payload)
        
        return payload

    def run(self):
        """Ejecuta el sensor en modo continuo."""
        self.running = True
        self.start_time = datetime.now()
        
        print(self._get_banner())
        print(f"📡 Endpoint: {self.config.api_endpoint}")
        print(f"🔄 Intervalo: {self.config.interval_seconds}s")
        print(f"📊 Modo API: {'Activo' if self.config.send_to_api else 'Solo simulación'}")
        print("─" * 70)
        print("Comandos disponibles: [a] Inyectar anomalía | [q] Salir")
        print("─" * 70 + "\n")
        
        try:
            while self.running:
                self.run_once()
                time.sleep(self.config.interval_seconds)
        except KeyboardInterrupt:
            self.stop()

    def run_async(self):
        """Ejecuta el sensor en un hilo separado."""
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()
        return self._thread

    def stop(self):
        """Detiene el sensor."""
        self.running = False
        print("\n" + "─" * 70)
        print(self._get_stats())
        print("─" * 70)
        print("👋 DataPulse Agent detenido.\n")

    def register_callback(self, callback: Callable):
        """Registra un callback que se ejecutará en cada lectura."""
        self._callbacks.append(callback)

    def _get_banner(self) -> str:
        """Retorna el banner del agente."""
        return """
╔══════════════════════════════════════════════════════════════════════════════╗
║                      🔥 DataPulse Agent v1.0 🔥                              ║
║                     Sensor IoT Virtual para Flow-Monitor                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

    def _get_stats(self) -> str:
        """Retorna las estadísticas del sensor."""
        runtime = datetime.now() - self.start_time if self.start_time else "N/A"
        anomaly_rate = (self.total_anomalies / self.total_readings * 100) if self.total_readings > 0 else 0
        
        return f"""
📊 ESTADÍSTICAS DE SESIÓN
   ├─ Lecturas totales: {self.total_readings}
   ├─ Anomalías generadas: {self.total_anomalies}
   ├─ Tasa de anomalías: {anomaly_rate:.1f}%
   └─ Tiempo de ejecución: {runtime}
"""


def interactive_mode(agent: DataPulseAgent):
    """Modo interactivo con comandos por teclado."""
    import sys
    import select
    
    # En sistemas Unix, podemos usar select para input no bloqueante
    if sys.platform != "win32":
        while agent.running:
            # Verificar si hay input disponible
            if select.select([sys.stdin], [], [], 0.1)[0]:
                cmd = sys.stdin.readline().strip().lower()
                if cmd == "a":
                    agent.inject_anomaly(duration=3)
                elif cmd == "q":
                    agent.stop()
                    break


def main():
    """Punto de entrada principal del script."""
    parser = argparse.ArgumentParser(
        description="🔥 DataPulse Agent - Sensor IoT Virtual para Flow-Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python datapulse_sensor.py                    # Modo simulación básico
  python datapulse_sensor.py --send-api         # Enviar datos al API
  python datapulse_sensor.py --interval 1       # Lecturas cada segundo
  python datapulse_sensor.py --anomaly-rate 0.1 # 10% de anomalías automáticas
        """
    )
    
    parser.add_argument(
        "--sensor-id",
        default="SENSOR_TEMP_01",
        help="ID del sensor (default: SENSOR_TEMP_01)"
    )
    parser.add_argument(
        "--location",
        default="Planta-A/Horno-Principal",
        help="Ubicación del sensor"
    )
    parser.add_argument(
        "--endpoint",
        default="http://localhost:8000/api/ingest",
        help="URL del endpoint de ingesta"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Intervalo entre lecturas en segundos (default: 2)"
    )
    parser.add_argument(
        "--send-api",
        action="store_true",
        help="Activar envío real al API (por defecto solo simulación)"
    )
    parser.add_argument(
        "--anomaly-rate",
        type=float,
        default=0.05,
        help="Probabilidad de anomalía automática 0-1 (default: 0.05)"
    )
    parser.add_argument(
        "--base-temp",
        type=float,
        default=30.0,
        help="Temperatura base de la onda (default: 30)"
    )
    parser.add_argument(
        "--amplitude",
        type=float,
        default=10.0,
        help="Amplitud de la onda senoidal (default: 10)"
    )
    
    args = parser.parse_args()
    
    # Crear configuración desde argumentos
    config = SensorConfig(
        sensor_id=args.sensor_id,
        location=args.location,
        api_endpoint=args.endpoint,
        interval_seconds=args.interval,
        send_to_api=args.send_api,
        auto_anomaly_probability=args.anomaly_rate,
        base_temp=args.base_temp,
        amplitude=args.amplitude
    )
    
    # Crear e iniciar el agente
    agent = DataPulseAgent(config)
    
    # Ejecutar el sensor en un hilo y manejar comandos interactivos
    agent.run_async()
    
    try:
        interactive_mode(agent)
    except Exception:
        # Fallback si el modo interactivo falla
        while agent.running:
            time.sleep(1)


if __name__ == "__main__":
    main()
