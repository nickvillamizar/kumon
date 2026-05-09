"""
app/routes/dashboard.py
══════════════════════════════════════════════════════════════════
Endpoints para alimentar el panel administrativo (edupanel_FINAL.html).

Expone:
  - GET /api/v1/dashboard/stats       → KPIs generales
  - GET /api/v1/dashboard/prospectos  → Lista paginada de prospectos
  - GET /api/v1/dashboard/jobs/recientes → Últimos 10 jobs
  - GET /api/v1/dashboard/health      → Verificar conexión BD
══════════════════════════════════════════════════════════════════
"""

from datetime import datetime, timedelta
from typing import Optional
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from config.database import get_db, DB_AVAILABLE
from app.mocks.mock_data import get_mock_stats, generate_mock_prospectos, get_mock_recent_jobs

logger = logging.getLogger(__name__)

# Importar solo si BD está disponible
if DB_AVAILABLE:
    try:
        from database.models import (
            ProcessingJob,
            Prospecto,
            TestResult,
            Student,
            TestTemplate,
            Bulletin,
            Role,
            Usuario,
        )
        from app.schemas.dashboard import (
            DashboardStatsResponse,
            ProspectoItemResponse,
            ProspectosPageResponse,
            JobRecenteItemResponse,
            JobsRecientesResponse,
            DashboardHealthResponse,
        )
    except Exception as e:
        logger.warning(f"No se pudieron importar modelos de BD: {e}")
        DB_AVAILABLE = False

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


# ══════════════════════════════════════════════════════════════════
# GET /api/v1/dashboard/stats
# ══════════════════════════════════════════════════════════════════

@router.get("/stats", summary="Estadísticas generales")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Retorna los KPIs principales del dashboard:
      - Totales: estudiantes, profesores, clases hoy, boletines
      - Distribución por semáforo (verde/amarillo/rojo)
      - Distribución por materia (MAT/ESP/ING)
      - Estado del pipeline (jobs en cola, procesando, completados hoy)
    """
    
    if not DB_AVAILABLE:
        logger.info("Usando MOCK DATA para /dashboard/stats")
        return get_mock_stats()
    
    try:
        # ── Totales generales ─────────────────────────────────────────
        total_estudiantes = db.query(func.count(Student.id_estudiante)).scalar() or 0
        total_profesores = db.query(func.count(Role.id_rol)).filter(
            Role.nombre_rol == "profesor"
        ).scalar() or 0

        # Aproximado: contar jobs completados hoy como "clases"
        today = datetime.now().date()
        clases_hoy = db.query(func.count(ProcessingJob.id_job)).filter(
            ProcessingJob.status == "done",
            func.DATE(ProcessingJob.completed_at) == today,
        ).scalar() or 0

        # Boletines generados
        boletines_generados = db.query(func.count(Bulletin.id_boletin)).scalar() or 0

        # ── Semáforo (desde TestResult) ────────────────────────────────
        semaforo_verde = db.query(func.count(TestResult.id_result)).filter(
            TestResult.semaforo == "verde"
        ).scalar() or 0

        semaforo_amarillo = db.query(func.count(TestResult.id_result)).filter(
            TestResult.semaforo == "amarillo"
        ).scalar() or 0

        semaforo_rojo = db.query(func.count(TestResult.id_result)).filter(
            TestResult.semaforo == "rojo"
        ).scalar() or 0

        # ── Materias (cuento por template subject) ─────────────────────
        # Contamos jobs por subject del template que usó
        mat_count = db.query(func.count(ProcessingJob.id_job)).join(
            TestTemplate, ProcessingJob.id_template == TestTemplate.id_template
        ).filter(TestTemplate.subject == "matematicas").scalar() or 0

        esp_count = db.query(func.count(ProcessingJob.id_job)).join(
            TestTemplate, ProcessingJob.id_template == TestTemplate.id_template
        ).filter(TestTemplate.subject == "espanol").scalar() or 0

        ing_count = db.query(func.count(ProcessingJob.id_job)).join(
            TestTemplate, ProcessingJob.id_template == TestTemplate.id_template
        ).filter(TestTemplate.subject == "ingles").scalar() or 0

        # ── Estado del pipeline ────────────────────────────────────────
        jobs_en_cola = db.query(func.count(ProcessingJob.id_job)).filter(
            ProcessingJob.status == "queued"
        ).scalar() or 0

        jobs_procesando = db.query(func.count(ProcessingJob.id_job)).filter(
            ProcessingJob.status == "processing"
        ).scalar() or 0

        jobs_completados_hoy = db.query(func.count(ProcessingJob.id_job)).filter(
            ProcessingJob.status == "done",
            func.DATE(ProcessingJob.completed_at) == today,
        ).scalar() or 0

        return {
            "total_estudiantes": total_estudiantes,
            "total_profesores": total_profesores,
            "clases_hoy": clases_hoy,
            "boletines_generados": boletines_generados,
            "semaforo_verde": semaforo_verde,
            "semaforo_amarillo": semaforo_amarillo,
            "semaforo_rojo": semaforo_rojo,
            "materias_matematicas": mat_count,
            "materias_espanol": esp_count,
            "materias_ingles": ing_count,
            "jobs_en_cola": jobs_en_cola,
            "jobs_procesando": jobs_procesando,
            "jobs_completados_hoy": jobs_completados_hoy,
        }
    except Exception as e:
        logger.error(f"Error en /dashboard/stats: {e}")
        return get_mock_stats()


# ══════════════════════════════════════════════════════════════════
# GET /api/v1/dashboard/prospectos
# ══════════════════════════════════════════════════════════════════

@router.get("/prospectos", summary="Lista paginada de prospectos")
async def get_prospectos(
    page: int = Query(1, ge=1, description="Página (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items por página"),
    db: Session = Depends(get_db),
):
    """
    Retorna lista paginada de prospectos con su último test y semáforo.
    """
    
    if not DB_AVAILABLE:
        logger.info("Usando MOCK DATA para /dashboard/prospectos")
        all_prospectos = generate_mock_prospectos(50)
        total = len(all_prospectos)
        offset = (page - 1) * page_size
        items = all_prospectos[offset:offset + page_size]
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items,
        }
    
    try:
        # Total de prospectos
        total = db.query(func.count(Prospecto.id_prospecto)).scalar() or 0

        # Query con offset/limit
        offset = (page - 1) * page_size
        prospectos = db.query(Prospecto).offset(offset).limit(page_size).all()

        items = []
        for prospecto in prospectos:
            # Buscar último test result de este prospecto
            last_result = db.query(TestResult).filter(
                TestResult.id_prospecto == prospecto.id_prospecto
            ).order_by(TestResult.created_at.desc()).first()

            # Buscar último job y boletín
            last_job = db.query(ProcessingJob).filter(
                ProcessingJob.id_prospecto == prospecto.id_prospecto
            ).order_by(ProcessingJob.created_at.desc()).first()

            has_boletin = (
                db.query(func.count(Bulletin.id_boletin)).filter(
                    Bulletin.id_result == last_result.id_result if last_result else None
                ).scalar() or 0
            ) > 0 if last_result else False

            item = {
                "id_prospecto": prospecto.id_prospecto,
                "nombre_completo": prospecto.nombre_completo,
                "grado_escolar": prospecto.grado_escolar,
                "nombre_escuela": prospecto.nombre_escuela,
                "fecha_prueba": prospecto.fecha_prueba.isoformat() if prospecto.fecha_prueba else None,
                "test_code": last_result.template.code if last_result and last_result.template else None,
                "subject": last_result.template.subject if last_result and last_result.template else None,
                "semaforo": last_result.semaforo if last_result else None,
                "percentage": last_result.percentage if last_result else None,
                "fecha_resultado": last_result.created_at if last_result else None,
                "tiene_boletin": has_boletin,
                "job_id": str(last_job.id_job) if last_job else None,
            }
            items.append(item)

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items,
        }
    except Exception as e:
        logger.error(f"Error en /dashboard/prospectos: {e}")
        return {
            "total": 0,
            "page": page,
            "page_size": page_size,
            "items": [],
        }


# ══════════════════════════════════════════════════════════════════
# GET /api/v1/dashboard/jobs/recientes
# ══════════════════════════════════════════════════════════════════

@router.get("/jobs/recientes", summary="Últimos 10 jobs del sistema")
async def get_jobs_recientes(db: Session = Depends(get_db)):
    """
    Retorna los últimos 10 jobs de procesamiento con su estado y resultado.
    """
    
    if not DB_AVAILABLE:
        logger.info("Usando MOCK DATA para /dashboard/jobs/recientes")
        jobs = get_mock_recent_jobs()
        return {
            "total_jobs": len(jobs),
            "jobs": jobs,
        }
    
    try:
        total_jobs = db.query(func.count(ProcessingJob.id_job)).scalar() or 0

        # Últimos 10 jobs ordenados por fecha descendente
        jobs = db.query(ProcessingJob).order_by(
            ProcessingJob.created_at.desc()
        ).limit(10).all()

        items = []
        for job in jobs:
            # Obtener nombre del sujeto
            if job.is_prospecto and job.prospecto:
                nombre_sujeto = job.prospecto.nombre_completo
                tipo_sujeto = "prospecto"
            elif job.is_estudiante and job.estudiante:
                nombre_sujeto = job.estudiante.nombre_completo
                tipo_sujeto = "estudiante"
            else:
                nombre_sujeto = "Desconocido"
                tipo_sujeto = "desconocido"

            # Obtener resultado si existe
            result = job.test_result
            test_code = result.template.code if result and result.template else None
            subject = result.template.subject if result and result.template else None
            semaforo = result.semaforo if result else None
            percentage = result.percentage if result else None

            item = {
                "id_job": job.id_job,
                "status": job.status,
                "progress_percent": job.progress_percent,
                "tipo_sujeto": tipo_sujeto,
                "nombre_sujeto": nombre_sujeto,
                "test_code": test_code,
                "subject": subject,
                "semaforo": semaforo,
                "percentage": percentage,
                "created_at": job.created_at,
                "completed_at": job.completed_at,
                "error_message": job.error_message,
            }
            items.append(item)

        return {
            "total_jobs": total_jobs,
            "jobs": items,
        }
    except Exception as e:
        logger.error(f"Error en /dashboard/jobs/recientes: {e}")
        return {
            "total_jobs": 0,
            "jobs": [],
        }


# ══════════════════════════════════════════════════════════════════
# GET /api/v1/dashboard/health
# ══════════════════════════════════════════════════════════════════


@router.get("/health", summary="Health check del dashboard")
async def get_dashboard_health(db: Session = Depends(get_db)):
    """
    Verifica que el backend y la BD estén operacionales.
    """
    
    if not DB_AVAILABLE:
        logger.info("Health check: BD no disponible, usando MOCK DATA")
        return {
            "status": "ok-mock",
            "db_connected": False,
            "message": "Dashboard funcionando con MOCK DATA (BD no disponible)",
        }
    
    try:
        # Intentar ejecutar una query simple
        db.query(Prospecto).limit(1).all()
        return {
            "status": "ok",
            "db_connected": True,
            "message": "Dashboard y BD funcionando correctamente",
        }
    except Exception as e:
        return {
            "status": "error",
            "db_connected": False,
            "message": f"Error de conexión: {str(e)}",
        }
