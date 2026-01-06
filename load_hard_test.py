#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                🔥🔥🔥 LOAD HARD TEST - STRESS TEST 🔥🔥🔥                    ║
║                   Prueba de Carga Extrema para Flow-Monitor                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

Test de carga agresivo diseñado para evaluar los límites del sistema.
Objetivo: saturar el backend y encontrar el punto de quiebre.

Usage:
    python load_hard_test.py                          # Modo estándar (100 req/s)
    python load_hard_test.py --rps 500                # 500 requests por segundo
    python load_hard_test.py --rps 1000 --duration 30 # 1000 req/s por 30 segundos
    python load_hard_test.py --chaos                  # Modo caos: bursts aleatorios
"""

import sys
import os
import time
import threading
import argparse
import random
import statistics
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from queue import Queue
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intelligence_core import IntelligenceService
from sensors.datapulse_sensor import DataPulseAgent, SensorConfig


@dataclass
class RequestMetrics:
    """Métricas de una request individual."""
    timestamp: float
    latency_ms: float
    success: bool
    status_code: int
    error: str = ""


@dataclass
class LoadTestResults:
    """Resultados agregados del test de carga."""
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    latencies: List[float] = field(default_factory=list)
    errors: Dict[str, int] = field(default_factory=dict)
    start_time: float = 0
    end_time: float = 0
    
    @property
    def success_rate(self) -> float:
        return (self.successful / self.total_requests * 100) if self.total_requests else 0
    
    @property
    def avg_latency(self) -> float:
        return statistics.mean(self.latencies) if self.latencies else 0
    
    @property
    def p50_latency(self) -> float:
        return statistics.median(self.latencies) if self.latencies else 0
    
    @property
    def p95_latency(self) -> float:
        if not self.latencies:
            return 0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[idx]
    
    @property
    def p99_latency(self) -> float:
        if not self.latencies:
            return 0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.99)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]
    
    @property
    def max_latency(self) -> float:
        return max(self.latencies) if self.latencies else 0
    
    @property
    def min_latency(self) -> float:
        return min(self.latencies) if self.latencies else 0
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time if self.end_time else 0
    
    @property
    def actual_rps(self) -> float:
        return self.total_requests / self.duration if self.duration else 0


class HardLoadTester:
    """
    🔥 Tester de carga extrema.
    
    Diseñado para saturar el sistema y encontrar sus límites.
    """
    
    def __init__(self, base_url: str = "http://localhost:8001",
                 target_rps: int = 100, 
                 num_workers: int = 50,
                 chaos_mode: bool = False):
        self.base_url = base_url
        self.target_rps = target_rps
        self.num_workers = min(num_workers, target_rps)
        self.chaos_mode = chaos_mode
        
        # Intelligence Core
        self.intelligence = IntelligenceService()
        self.intelligence.configure_threshold("temperature", max_temp=60, warning_temp=80, critical_temp=90)
        
        # Resultados
        self.results = LoadTestResults()
        self._lock = threading.Lock()
        self.running = False
        
        # Configuraciones de sensores variados
        self.sensor_configs = [
            {"id": f"STRESS_{i:03d}", "location": f"Zona-{chr(65 + i % 26)}/Equipo-{i}", 
             "base_temp": 25 + (i % 40), "amplitude": 5 + (i % 15)}
            for i in range(100)
        ]
    
    def _generate_payload(self) -> dict:
        """Genera un payload aleatorio para el test."""
        cfg = random.choice(self.sensor_configs)
        
        sensor_config = SensorConfig(
            sensor_id=cfg["id"],
            location=cfg["location"],
            base_temp=cfg["base_temp"],
            amplitude=cfg["amplitude"],
            auto_anomaly_probability=0.15  # 15% anomalías para más estrés
        )
        sensor = DataPulseAgent(sensor_config)
        reading = sensor.generate_reading()
        
        enriched = self.intelligence.process(reading)
        enriched_dict = enriched.to_dict()
        
        return {
            "data_original": enriched_dict["data_original"],
            "risk_level": enriched_dict["risk_level"],
            "prediction_alert": enriched_dict["prediction_alert"],
            "processed_at": datetime.now().isoformat()
        }
    
    def _send_request(self) -> RequestMetrics:
        """Envía una request y mide el tiempo."""
        start = time.perf_counter()
        try:
            payload = self._generate_payload()
            response = requests.post(
                f"{self.base_url}/api/dashboard/process",
                json=payload,
                timeout=10
            )
            latency = (time.perf_counter() - start) * 1000
            
            return RequestMetrics(
                timestamp=time.time(),
                latency_ms=latency,
                success=response.status_code == 200,
                status_code=response.status_code
            )
        except requests.Timeout:
            return RequestMetrics(
                timestamp=time.time(),
                latency_ms=(time.perf_counter() - start) * 1000,
                success=False,
                status_code=0,
                error="TIMEOUT"
            )
        except requests.ConnectionError as e:
            return RequestMetrics(
                timestamp=time.time(),
                latency_ms=(time.perf_counter() - start) * 1000,
                success=False,
                status_code=0,
                error=f"CONNECTION_ERROR: {str(e)[:50]}"
            )
        except Exception as e:
            return RequestMetrics(
                timestamp=time.time(),
                latency_ms=(time.perf_counter() - start) * 1000,
                success=False,
                status_code=0,
                error=str(e)[:50]
            )
    
    def _worker(self, request_queue: Queue):
        """Worker que procesa requests de la cola."""
        while self.running:
            try:
                # Obtener trabajo de la cola (con timeout para poder verificar running)
                try:
                    _ = request_queue.get(timeout=0.1)
                except:
                    continue
                
                metrics = self._send_request()
                
                with self._lock:
                    self.results.total_requests += 1
                    self.results.latencies.append(metrics.latency_ms)
                    
                    if metrics.success:
                        self.results.successful += 1
                    else:
                        self.results.failed += 1
                        error_key = metrics.error or f"HTTP_{metrics.status_code}"
                        self.results.errors[error_key] = self.results.errors.get(error_key, 0) + 1
                
                request_queue.task_done()
            except Exception:
                pass
    
    def _chaos_burst(self, request_queue: Queue):
        """Genera bursts caóticos de requests."""
        while self.running:
            # Burst aleatorio de 50-200 requests
            burst_size = random.randint(50, 200)
            for _ in range(burst_size):
                if not self.running:
                    break
                request_queue.put(1)
            
            # Pausa aleatoria
            pause = random.uniform(0.1, 0.5)
            time.sleep(pause)
    
    def _rate_limiter(self, request_queue: Queue):
        """Mantiene el rate de requests constante."""
        interval = 1.0 / self.target_rps
        
        while self.running:
            request_queue.put(1)
            time.sleep(interval)
    
    def _print_live_stats(self):
        """Imprime estadísticas en tiempo real."""
        last_count = 0
        while self.running:
            time.sleep(1)
            if not self.running:
                break
            
            with self._lock:
                current = self.results.total_requests
                rps = current - last_count
                success_rate = self.results.success_rate
                avg_lat = self.results.avg_latency
                failed = self.results.failed
            
            last_count = current
            
            # Indicador de salud
            if success_rate >= 99:
                health = "🟢"
            elif success_rate >= 95:
                health = "🟡"
            elif success_rate >= 80:
                health = "🟠"
            else:
                health = "🔴"
            
            print(f"\r{health} [{current:,} total] [{rps:,}/s actual] "
                  f"[✅ {success_rate:.1f}%] [⏱️ {avg_lat:.0f}ms avg] "
                  f"[❌ {failed}]", end="", flush=True)
    
    def run(self, duration: int = 30):
        """
        Ejecuta el test de carga.
        
        Args:
            duration: Duración en segundos
        """
        print(self._get_banner())
        print(f"🎯 Target RPS: {self.target_rps}")
        print(f"👷 Workers: {self.num_workers}")
        print(f"⏳ Duración: {duration}s")
        print(f"🌀 Modo Caos: {'Activado' if self.chaos_mode else 'Desactivado'}")
        print("─" * 70)
        
        # Verificar conexión
        try:
            health = requests.get(f"{self.base_url}/health", timeout=3)
            if health.status_code == 200:
                print("✅ Backend conectado")
            else:
                print(f"⚠️ Backend respondió: {health.status_code}")
        except Exception as e:
            print(f"❌ No se pudo conectar al backend: {e}")
            return
        
        print("─" * 70)
        print("\n🚀 Iniciando test de carga extrema...\n")
        
        self.running = True
        self.results.start_time = time.time()
        
        request_queue = Queue()
        
        # Iniciar workers
        workers = []
        for _ in range(self.num_workers):
            t = threading.Thread(target=self._worker, args=(request_queue,), daemon=True)
            t.start()
            workers.append(t)
        
        # Iniciar generador de requests
        if self.chaos_mode:
            rate_thread = threading.Thread(target=self._chaos_burst, args=(request_queue,), daemon=True)
        else:
            rate_thread = threading.Thread(target=self._rate_limiter, args=(request_queue,), daemon=True)
        rate_thread.start()
        
        # Iniciar monitor de stats
        stats_thread = threading.Thread(target=self._print_live_stats, daemon=True)
        stats_thread.start()
        
        try:
            time.sleep(duration)
        except KeyboardInterrupt:
            print("\n\n⚠️ Test interrumpido por usuario")
        
        self.running = False
        self.results.end_time = time.time()
        
        # Esperar a que terminen las requests pendientes
        time.sleep(1)
        
        print("\n\n")
        self._print_report()
    
    def _get_banner(self) -> str:
        return """
╔══════════════════════════════════════════════════════════════════════════════╗
║                🔥🔥🔥 LOAD HARD TEST - STRESS TEST 🔥🔥🔥                    ║
║                   Prueba de Carga Extrema para Flow-Monitor                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    
    def _print_report(self):
        """Imprime el reporte final detallado."""
        r = self.results
        
        print("═" * 70)
        print("              📊 REPORTE DE STRESS TEST - RESULTADOS")
        print("═" * 70)
        
        # Determinar estado del sistema
        if r.success_rate >= 99 and r.p95_latency < 100:
            status = "🟢 SISTEMA SALUDABLE"
            verdict = "El sistema manejó la carga sin problemas"
        elif r.success_rate >= 95 and r.p95_latency < 500:
            status = "🟡 SISTEMA BAJO PRESIÓN"
            verdict = "El sistema mostró signos de estrés pero se mantuvo estable"
        elif r.success_rate >= 80:
            status = "🟠 SISTEMA DEGRADADO"
            verdict = "El sistema experimentó degradación significativa"
        else:
            status = "🔴 SISTEMA SOBRECARGADO"
            verdict = "¡El sistema colapsó bajo la carga!"
        
        print(f"""
{status}
{verdict}

📈 MÉTRICAS GENERALES
   ├─ Total Requests: {r.total_requests:,}
   ├─ Exitosas: {r.successful:,} ({r.success_rate:.2f}%)
   ├─ Fallidas: {r.failed:,} ({100 - r.success_rate:.2f}%)
   ├─ Duración: {r.duration:.1f}s
   └─ RPS Real: {r.actual_rps:.1f} req/s

⏱️ LATENCIAS (ms)
   ├─ Mínima: {r.min_latency:.1f}ms
   ├─ Promedio: {r.avg_latency:.1f}ms
   ├─ P50 (mediana): {r.p50_latency:.1f}ms
   ├─ P95: {r.p95_latency:.1f}ms
   ├─ P99: {r.p99_latency:.1f}ms
   └─ Máxima: {r.max_latency:.1f}ms
""")
        
        if r.errors:
            print("❌ ERRORES ENCONTRADOS:")
            for error, count in sorted(r.errors.items(), key=lambda x: -x[1]):
                print(f"   ├─ {error}: {count}")
        
        # Recomendaciones
        print("\n💡 ANÁLISIS:")
        if r.success_rate < 95:
            print("   ⚠️ Tasa de éxito por debajo del umbral aceptable (95%)")
        if r.p95_latency > 200:
            print("   ⚠️ Latencia P95 elevada (>200ms) - considerar optimización")
        if r.p99_latency > 1000:
            print("   ⚠️ Latencia P99 muy alta (>1s) - posibles timeouts en producción")
        if "CONNECTION_ERROR" in str(r.errors):
            print("   ⚠️ Errores de conexión detectados - posible agotamiento de recursos")
        if "TIMEOUT" in str(r.errors):
            print("   ⚠️ Timeouts detectados - backend saturado")
        
        if r.success_rate >= 99 and r.p95_latency < 100:
            print("   ✅ Sistema puede manejar más carga. Incrementar RPS para encontrar límite.")
        
        print("\n" + "═" * 70)
        print("🏁 Test de carga finalizado")
        print("═" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="🔥 Load Hard Test - Stress Test Extremo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python load_hard_test.py                          # 100 req/s, 30s
  python load_hard_test.py --rps 500                # 500 req/s
  python load_hard_test.py --rps 1000 --duration 60 # 1000 req/s por 1 min
  python load_hard_test.py --chaos                  # Modo caos con bursts
  python load_hard_test.py --rps 2000 --workers 100 # Alta concurrencia
        """
    )
    
    parser.add_argument("--rps", "-r", type=int, default=100,
                        help="Target de requests por segundo (default: 100)")
    parser.add_argument("--duration", "-d", type=int, default=30,
                        help="Duración en segundos (default: 30)")
    parser.add_argument("--workers", "-w", type=int, default=50,
                        help="Número de workers/threads (default: 50)")
    parser.add_argument("--chaos", action="store_true",
                        help="Modo caos: bursts aleatorios en lugar de rate constante")
    parser.add_argument("--url", "-u", default="http://localhost:8001",
                        help="URL base del backend")
    
    args = parser.parse_args()
    
    tester = HardLoadTester(
        base_url=args.url,
        target_rps=args.rps,
        num_workers=args.workers,
        chaos_mode=args.chaos
    )
    
    tester.run(duration=args.duration)


if __name__ == "__main__":
    main()
