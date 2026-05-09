# app/mocks/mock_data.py
"""
Mock data para desarrollo cuando PostgreSQL no está disponible.
Se usa como fallback en get_db() si la conexión falla.
"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Any
import random

# ════════════════════════════════════════════════════════════════════════════════
# MOCK STATS
# ════════════════════════════════════════════════════════════════════════════════

def get_mock_stats() -> Dict[str, Any]:
    """Retorna estadísticas mock para el dashboard"""
    return {
        "total_estudiantes": random.randint(50, 150),
        "total_profesores": random.randint(5, 15),
        "clases_hoy": random.randint(3, 12),
        "boletines_generados": random.randint(100, 500),
        "semaforo_verde": random.randint(30, 80),
        "semaforo_amarillo": random.randint(20, 60),
        "semaforo_rojo": random.randint(10, 40),
        "materias_matematicas": random.randint(40, 120),
        "materias_espanol": random.randint(35, 100),
        "materias_ingles": random.randint(25, 80),
        "jobs_en_cola": random.randint(0, 5),
        "jobs_procesando": random.randint(0, 3),
        "jobs_completados_hoy": random.randint(5, 20),
    }


# ════════════════════════════════════════════════════════════════════════════════
# MOCK PROSPECTOS
# ════════════════════════════════════════════════════════════════════════════════

NOMBRES = [
    "Juan", "María", "Carlos", "Ana", "Luis", "Sofía", "Pedro", "Isabella",
    "Diego", "Valentina", "Miguel", "Camila", "Francisco", "Laura", "Antonio"
]

APELLIDOS = [
    "García", "López", "Martínez", "González", "Rodríguez", "Pérez", "Sánchez",
    "Ramírez", "Torres", "Flores", "Rivera", "Cruz", "Silva", "Morales"
]

ESCUELAS = [
    "Colegio Distrital", "Instituto Técnico", "Liceo Colombiano", "Gimnasio Moderno",
    "Colegio Bilingüe", "Escuela Rural", "Colegio Privado", "Unidad Educativa"
]

MATERIAS = ["matematicas", "espanol", "ingles"]

SEMAFOROS = ["verde", "amarillo", "rojo"]

def generate_mock_prospectos(count: int = 30) -> List[Dict[str, Any]]:
    """Genera una lista de prospectos fake"""
    prospectos = []
    for i in range(count):
        nombre = f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)}"
        grado = random.randint(1, 11)
        subject = random.choice(MATERIAS)
        semaforo = random.choice(SEMAFOROS)
        
        prospectos.append({
            "id_prospecto": f"PROSP-{i+1:05d}",
            "nombre_completo": nombre,
            "grado_escolar": grado,
            "nombre_escuela": random.choice(ESCUELAS),
            "fecha_prueba": (datetime.now() - timedelta(days=random.randint(0, 30))).date().isoformat(),
            "test_code": f"TEST-{subject[:3].upper()}-{random.randint(100, 999)}",
            "subject": subject,
            "semaforo": semaforo,
            "percentage": random.randint(40, 100),
            "fecha_resultado": (datetime.now() - timedelta(days=random.randint(0, 7))).isoformat(),
            "tiene_boletin": random.choice([True, False]),
            "job_id": f"JOB-{random.randint(1000, 9999)}",
        })
    
    return prospectos


# ════════════════════════════════════════════════════════════════════════════════
# MOCK JOBS RECIENTES
# ════════════════════════════════════════════════════════════════════════════════

def get_mock_recent_jobs() -> List[Dict[str, Any]]:
    """Retorna últimos 10 jobs fake"""
    jobs = []
    for i in range(10):
        status = random.choice(["done", "processing", "queued"])
        created_at = datetime.now() - timedelta(hours=random.randint(0, 48))
        
        job = {
            "id_job": f"JOB-{9000-i:05d}",
            "id_prospecto": f"PROSP-{random.randint(1, 100):05d}",
            "status": status,
            "subject": random.choice(MATERIAS),
            "created_at": created_at.isoformat(),
            "completed_at": (created_at + timedelta(minutes=random.randint(5, 30))).isoformat() if status == "done" else None,
            "video_filename": f"video_{random.randint(1000, 9999)}.mp4" if random.random() > 0.3 else None,
            "error_message": None if status != "error" else "Timeout en procesamiento",
        }
        jobs.append(job)
    
    return sorted(jobs, key=lambda x: x["created_at"], reverse=True)
