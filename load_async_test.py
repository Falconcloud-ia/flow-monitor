#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           🚀 ASYNC HYPER-LOAD TEST - INDUSTRIAL GRADE 🚀                     ║
║           Objetivo: > 2,000,000 Peticiones (Simulación Crítica)              ║
╚══════════════════════════════════════════════════════════════════════════════╝

Este script utiliza AIOHTTP y UVLOOP para generar carga masiva asíncrona.
Es capaz de generar miles de peticiones por segundo (RPS) desde un solo nodo.

Uso:
    python load_async_test.py --total 2000000 --concurrency 500
"""

import asyncio
import uvloop
import aiohttp
import time
import random
import argparse
from datetime import datetime
from dataclasses import dataclass

# Instalar uvloop como la política por defecto
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

@dataclass
class Stats:
    sent: int = 0
    success: int = 0
    failed: int = 0
    errors: int = 0
    start_time: float = 0
    end_time: float = 0

def generate_payload(req_id):
    """Payload ligero pre-calculado para velocidad."""
    temp = random.uniform(20.0, 110.0)
    risk = "LOW"
    if temp > 90: risk = "CRITICAL"
    elif temp > 80: risk = "HIGH"
    elif temp > 60: risk = "MEDIUM"
    
    return {
        "data_original": {
            "sensor_id": f"SENS_{req_id % 1000}",
            "timestamp": datetime.now().isoformat(),
            "value": round(temp, 2),
            "unit": "Celsius",
            "_meta": {"status": "ASYNC_TEST"}
        },
        "risk_level": risk,
        "prediction_alert": {"p": 0.1},
        "processed_at": datetime.now().isoformat()
    }

async def worker(session, url, stats, total_target, progress_bar=True):
    """Worker asíncrono que bombardea la API."""
    while stats.sent < total_target:
        # Incremento optimista anticipado para velocidad
        current_id = stats.sent
        stats.sent += 1
        
        if current_id >= total_target:
            break
            
        try:
            payload = generate_payload(current_id)
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    stats.success += 1
                else:
                    stats.failed += 1
                    # Leer cuerpo de error solo si es necesario para debug (lento)
                    # await response.text() 
        except Exception:
            stats.errors += 1

async def monitor(stats, total_target):
    """Monitor de progreso en tiempo real."""
    print("⏳ Iniciando calentamiento de motores...")
    await asyncio.sleep(1)
    
    while stats.sent < total_target:
        elapsed = time.time() - stats.start_time
        if elapsed == 0: elapsed = 0.001
        
        rps = stats.sent / elapsed
        percent = (stats.sent / total_target) * 100
        
        # Barra de progreso
        bar = '█' * int(percent / 4) + '░' * (25 - int(percent / 4))
        
        print(f"\r🚀 [{bar}] {percent:5.1f}% | Req: {stats.sent:,} | RPS: {rps:,.0f} | Err: {stats.failed + stats.errors}", end="", flush=True)
        await asyncio.sleep(0.5)
        
        # Si llevamos mucho tiempo (safety break)
        # if elapsed > 300: break 

async def main():
    parser = argparse.ArgumentParser(description="Async Load Test")
    parser.add_argument("--total", type=int, default=2000000, help="Total requests")
    parser.add_argument("--concurrency", type=int, default=200, help="Conexiones concurrentes")
    parser.add_argument("--url", default="http://localhost:8001/api/dashboard/process")
    args = parser.parse_args()

    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║             🚀  PRUEBA DE ESTRÉS ASÍNCRONA (AIOHTTP) 🚀                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ 🎯 Objetivo:   {args.total:,} peticiones                                     ║
║ ⚡ Concurrencia: {args.concurrency} clientes simultáneos                       ║
║ 🔗 Endpoint:   {args.url}                                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

    stats = Stats()
    stats.start_time = time.time()
    
    # Configuración de rendimiento de TCP
    conn = aiohttp.TCPConnector(limit=args.concurrency, ttl_dns_cache=300)
    
    timeout = aiohttp.ClientTimeout(total=10) # 10s timeout
    
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        # Lanzar monitor
        monitor_task = asyncio.create_task(monitor(stats, args.total))
        
        # Lanzar workers
        workers = [asyncio.create_task(worker(session, args.url, stats, args.total)) 
                   for _ in range(args.concurrency)]
        
        # Esperar a que terminen
        await asyncio.gather(*workers)
        
        # Asegurar que el monitor termine
        await monitor_task

    stats.end_time = time.time()
    duration = stats.end_time - stats.start_time
    total_reqs = stats.success + stats.failed + stats.errors
    rps = total_reqs / duration if duration > 0 else 0
    
    print("\n\n" + "═" * 70)
    print("📊 REPORTE FINAL DE ESTRÉS ASÍNCRONO")
    print("═" * 70)
    print(f"⏱️  Duración:          {duration:.2f} segundos")
    print(f"📨 Solicitudes:       {total_reqs:,}")
    print(f"✅ Exitosas:          {stats.success:,}")
    print(f"❌ Fallidas/Err:      {stats.failed + stats.errors:,}")
    print(f"⚡ Throughput (RPS):  {rps:,.0f} req/s")
    print("═" * 70)
    
    # Análisis de Infraestructura IA
    print("\n🏗️  PLAN DE INFRAESTRUCTURA RECOMENDADO:")
    required_rps_2m_5min = 6666  # 2M en 5 mins
    scaling_factor = max(1, required_rps_2m_5min / (rps if rps > 0 else 1))
    
    print(f"   Basado en el rendimiento actual de un solo nodo ({rps:.0f} RPS):")
    print(f"   1. **Kubernetes Cluster**: Se necesitan aprox {scaling_factor:.1f}x veces esta capacidad.")
    print(f"   2. **HPA Rules**: Configurar escalado cuando CPU > 70% o RPS por pod > {rps*.8:.0f}.")
    print(f"   3. **Ingress**: Implementar NGINX optimizado para 'Keep-Alive'.")
    print(f"   4. **Message Queue**: REDIS o KAFKA es mandatorio entre capas.")

if __name__ == "__main__":
    asyncio.run(main())
