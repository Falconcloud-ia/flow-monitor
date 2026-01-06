#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║             ☢️  FLOW-MONITOR EXTREME LOAD TEST (NUCLEAR MODE) ☢️             ║
║                 Objetivo: > 2,000,000 Peticiones / Ciclo                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

Este script utiliza MULTIPROCESSING para evadir el GIL de Python y saturar
completamente la interfaz de red local y el backend.

ADVERTENCIA:
    - Esto consumirá mucha CPU.
    - Puede causar denegación de servicio (DoS) local.
    - Diseñado para evaluar infraestructura crítica.

Uso:
    python load_extreme_test.py --total 2000000 --processes 8 --threads 50
"""

import sys
import os
import time
import multiprocessing
import threading
import requests
import random
from datetime import datetime
from queue import Empty
import argparse

# Agregar path para imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Importamos clases base pero las re-implementaremos ligeras para velocidad máxima
# from intelligence_core import IntelligenceService 
# NOTA: Para velocidad extrema, generaremos payloads "pre-calculados" o ligeros
# invocar toda la lógica de IntelligenceService en el generador de carga es un cuello de botella.
# Simularemos la salida del sensor directamente.

def generate_fast_payload(sensor_id):
    """Genera payload optimizado para velocidad."""
    temp = random.uniform(20.0, 110.0)
    
    # Lógica simplificada de "intelligence" para no gastar CPU en el generador
    risk = "LOW"
    if temp > 90: risk = "CRITICAL"
    elif temp > 80: risk = "HIGH"
    elif temp > 60: risk = "MEDIUM"
    
    return {
        "data_original": {
            "sensor_id": sensor_id,
            "timestamp": datetime.now().isoformat(),
            "value": round(temp, 2),
            "unit": "Celsius",
            "_meta": {"status": "STRESS_TEST"}
        },
        "risk_level": risk,
        "prediction_alert": {
            "failure_probability": random.random(),
            "predicted_failure_time": None
        },
        "processed_at": datetime.now().isoformat()
    }

def worker_process(proc_id, target_url, limit_requests, num_threads, shared_counter, error_counter, start_event):
    """
    Función que ejecuta un PROCESO completo.
    Lanza múltiples hilos para realizar peticiones HTTP.
    """
    
    # Esperar señal de inicio para coordinar ataque simultáneo
    start_event.wait()
    
    session = requests.Session()
    # Optimización de conexión
    adapter = requests.adapters.HTTPAdapter(pool_connections=num_threads, pool_maxsize=num_threads)
    session.mount('http://', adapter)
    
    local_count = 0
    local_errors = 0
    
    def thread_task():
        nonlocal local_count, local_errors
        while True:
            # Verificación "suelta" para rendimiento (no lockear en cada iteración)
            if shared_counter.value >= limit_requests:
                break
                
            try:
                # Generar payload rápido
                payload = generate_fast_payload(f"PROC_{proc_id}_THREAD_{threading.get_ident()}")
                
                resp = session.post(target_url, json=payload, timeout=5)
                
                if resp.status_code == 200:
                    local_count += 1
                    # Actualizar contador compartido en lotes para evitar contención de lock
                    if local_count % 100 == 0:
                        with shared_counter.get_lock():
                            shared_counter.value += 100
                else:
                    local_errors += 1
                    with error_counter.get_lock():
                        error_counter.value += 1
                        
            except Exception:
                local_errors += 1
                with error_counter.get_lock():
                    error_counter.value += 1
    
    threads = []
    for _ in range(num_threads):
        t = threading.Thread(target=thread_task)
        t.daemon = True
        t.start()
        threads.append(t)
        
    for t in threads:
        t.join()

    # Actualizar remanente
    rem = local_count % 100
    if rem > 0:
        with shared_counter.get_lock():
            shared_counter.value += rem


def monitor(shared_counter, error_counter, total_target, start_time):
    """Hilo de monitoreo en el proceso principal."""
    try:
        while True:
            time.sleep(1)
            current = shared_counter.value
            errors = error_counter.value
            elapsed = time.time() - start_time
            
            if elapsed == 0: continue
            
            rps = current / elapsed
            progress = (current / total_target) * 100
            
            # Barra de progreso visual
            bar_len = 30
            filled_len = int(bar_len * current // total_target)
            bar = '█' * filled_len + '░' * (bar_len - filled_len)
            
            print(f"\r🚀 [{bar}] {progress:5.1f}% | "
                  f"Req: {current:,} / {total_target:,} | "
                  f"Errors: {errors:,} | "
                  f"RPS: {rps:,.0f}", end="", flush=True)
            
            if current >= total_target:
                break
    except KeyboardInterrupt:
        pass

def main():
    parser = argparse.ArgumentParser(description="Nuclear Stress Test")
    parser.add_argument("--total", type=int, default=2000000, help="Total de peticiones objetivo")
    parser.add_argument("--processes", type=int, default=multiprocessing.cpu_count(), help="Número de procesos CPU")
    parser.add_argument("--threads", type=int, default=50, help="Hilos por proceso")
    parser.add_argument("--url", default="http://localhost:8001/api/dashboard/process", help="Endpoint destino")
    
    args = parser.parse_args()
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║             ☢️  INICIANDO PRUEBA DE ESTRÉS EXTREMA  ☢️                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ 🎯 Objetivo:   {args.total:,} peticiones                                     ║
║ 🔧 Workers:    {args.processes} Procesos x {args.threads} Hilos = {args.processes * args.threads} Concurrencia ║
║ 🔗 Endpoint:   {args.url}                                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Objetos compartidos
    manager = multiprocessing.Manager()
    shared_counter = multiprocessing.Value('i', 0)
    error_counter = multiprocessing.Value('i', 0)
    start_event = multiprocessing.Event()
    
    # Crear procesos
    processes = []
    
    # Dividimos el objetivo "virtualmente", pero todos suman al shared_counter
    # Pasamos limit_requests muy alto al worker para que paren por el contador global logic (o aproximado)
    # Mejor: que cada worker pare cuando vea el shared_counter lleno.
    
    print("🔥 Preparando ojivas (creando procesos)...")
    
    for i in range(args.processes):
        p = multiprocessing.Process(
            target=worker_process,
            args=(i, args.url, args.total, args.threads, shared_counter, error_counter, start_event)
        )
        processes.append(p)
        p.start()
        
    print("🔥 Procesos listos. ¡LANZANDO ATAQUE!")
    start_time = time.time()
    start_event.set() # Iniciar todos a la vez
    
    # Monitoreo
    monitor(shared_counter, error_counter, args.total, start_time)
    
    # Esperar terminación
    for p in processes:
        p.join()
        
    end_time = time.time()
    duration = end_time - start_time
    total_reqs = shared_counter.value
    actual_rps = total_reqs / duration if duration > 0 else 0
    
    print("\n\n" + "═" * 70)
    print("📊 REPORTE DE INFRAESTRUCTURA - RESULTADO FINAL")
    print("═" * 70)
    print(f"⏱️  Duración Total:      {duration:.2f} segundos")
    print(f"📨 Peticiones Totales:  {total_reqs:,}")
    print(f"❌ Errores:             {error_counter.value:,} ({(error_counter.value/total_reqs*100):.2f}%)")
    print(f"⚡ Throughput (RPS):    {actual_rps:,.2f} req/s")
    print("═" * 70)
    
    # Evaluación para Kubernetes
    print("\n💡 EVALUACIÓN PARA KUBERNETES & IAC:")
    if actual_rps > 5000:
        print("✅ EXCELENTE RENDIMIENTO: La aplicación maneja alta concurrencia.")
        print("   Recomendación: Cluster K8s estándar con HPA (Horizontal Pod Autoscaler) basado en CPU.")
    elif actual_rps > 1000:
        print("⚠️ RENDIMIENTO MODERADO: Puede requerir optimización de código o más réplicas.")
        print("   Recomendación: K8s con múltiples réplicas (min 3-5) y caching (Redis).")
    else:
        print("🔴 CUELLO DE BOTELLA DETECTADO: El backend actual no soporta carga industrial masiva.")
        print("   Recomendación: REFACTORIZAR a arquitectura asíncrona pura o Go/Rust para Ingestion.")
        print("   K8s requerirá escalado agresivo de pods.")

if __name__ == "__main__":
    main()
