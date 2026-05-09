"""
app/routes/dashboard.py

Endpoints para alimentar el panel administrativo (edupanel_FINAL.html).

Expone:
  - GET /api/v1/dashboard/stats          -> KPIs generales
  - GET /api/v1/dashboard/prospectos     -> Lista paginada de prospectos
  - GET /api/v1/dashboard/jobs/recientes -> Ultimos 10 jobs
  - GET /api/v1/dashboard/health         -> Verificar conexion BD
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from config.database import get_db
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

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def _safe_count(db: Session, query) -> int:
    """Ejecuta un conteo y retorna 0 si hay error de columna inexistente."""
    try:
        return query.scalar() or 0
    except Exception:
        db.rollback()
        return 0


@router.get("/stats", response_model=DashboardStatsResponse, summary="Estadisticas generales")
async def get_dashboard_stats(db: Session = Depends(get_db)) -> DashboardStatsResponse:
    today = datetime.now().date()

    total_estudiantes = _safe_count(db, db.query(func.count(Student.id_estudiante)))
    total_profesores = _safe_count(
        db,
        db.query(func.count(Role.id_rol)).filter(Role.nombre_rol == "profesor"),
    )
    clases_hoy = _safe_count(
        db,
        db.query(func.count(ProcessingJob.id_job)).filter(
            ProcessingJob.status == "done",
            func.DATE(ProcessingJob.created_at) == today,
        ),
    )
    boletines_generados = _safe_count(db, db.query(func.count(Bulletin.id_bulletin)))
    semaforo_verde = _safe_count(
        db,
        db.query(func.count(TestResult.id_result)).filter(TestResult.semaforo == "verde"),
    )
    semaforo_amarillo = _safe_count(
        db,
        db.query(func.count(TestResult.id_result)).filter(TestResult.semaforo == "amarillo"),
    )
    semaforo_rojo = _safe_count(
        db,
        db.query(func.count(TestResult.id_result)).filter(TestResult.semaforo == "rojo"),
    )
    mat_count = _safe_count(
        db,
        db.query(func.count(ProcessingJob.id_job))
        .join(TestTemplate, ProcessingJob.id_template == TestTemplate.id_template)
        .filter(TestTemplate.subject == "matematicas"),
    )
    esp_count = _safe_count(
        db,
        db.query(func.count(ProcessingJob.id_job))
        .join(TestTemplate, ProcessingJob.id_template == TestTemplate.id_template)
        .filter(TestTemplate.subject == "espanol"),
    )
    ing_count = _safe_count(
        db,
        db.query(func.count(ProcessingJob.id_job))
        .join(TestTemplate, ProcessingJob.id_template == TestTemplate.id_template)
        .filter(TestTemplate.subject == "ingles"),
    )
    jobs_en_cola = _safe_count(
        db,
        db.query(func.count(ProcessingJob.id_job)).filter(ProcessingJob.status == "queued"),
    )
    jobs_procesando = _safe_count(
        db,
        db.query(func.count(ProcessingJob.id_job)).filter(ProcessingJob.status == "processing"),
    )
    jobs_completados_hoy = _safe_count(
        db,
        db.query(func.count(ProcessingJob.id_job)).filter(
            ProcessingJob.status == "done",
            func.DATE(ProcessingJob.created_at) == today,
        ),
    )

    return DashboardStatsResponse(
        total_estudiantes=total_estudiantes,
        total_profesores=total_profesores,
        clases_hoy=clases_hoy,
        boletines_generados=boletines_generados,
        semaforo_verde=semaforo_verde,
        semaforo_amarillo=semaforo_amarillo,
        semaforo_rojo=semaforo_rojo,
        materias_matematicas=mat_count,
        materias_espanol=esp_count,
        materias_ingles=ing_count,
        jobs_en_cola=jobs_en_cola,
        jobs_procesando=jobs_procesando,
        jobs_completados_hoy=jobs_completados_hoy,
    )


@router.get(
    "/prospectos",
    response_model=ProspectosPageResponse,
    summary="Lista paginada de prospectos",
)
async def get_prospectos(
    page: int = Query(1, ge=1, description="Pagina (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items por pagina"),
    db: Session = Depends(get_db),
) -> ProspectosPageResponse:
    total = db.query(func.count(Prospecto.id_prospecto)).scalar() or 0
    offset = (page - 1) * page_size
    prospectos = db.query(Prospecto).offset(offset).limit(page_size).all()

    items = []
    for prospecto in prospectos:
        last_result = (
            db.query(TestResult)
            .filter(TestResult.id_prospecto == prospecto.id_prospecto)
            .order_by(TestResult.created_at.desc())
            .first()
        )
        last_job = (
            db.query(ProcessingJob)
            .filter(ProcessingJob.id_prospecto == prospecto.id_prospecto)
            .order_by(ProcessingJob.created_at.desc())
            .first()
        )

        has_boletin = False
        if last_result:
            has_boletin = (
                db.query(func.count(Bulletin.id_bulletin))
                .filter(Bulletin.id_result == last_result.id_result)
                .scalar() or 0
            ) > 0

        item = ProspectoItemResponse(
            id_prospecto=prospecto.id_prospecto,
            nombre_completo=prospecto.nombre_completo,
            grado_escolar=prospecto.grado_escolar,
            nombre_escuela=prospecto.nombre_escuela,
            fecha_prueba=(
                prospecto.fecha_prueba.isoformat() if prospecto.fecha_prueba else None
            ),
            test_code=(
                last_result.template.code if last_result and last_result.template else None
            ),
            subject=(
                last_result.template.subject if last_result and last_result.template else None
            ),
            semaforo=last_result.semaforo if last_result else None,
            percentage=last_result.percentage if last_result else None,
            fecha_resultado=last_result.created_at if last_result else None,
            tiene_boletin=has_boletin,
            job_id=str(last_job.id_job) if last_job else None,
        )
        items.append(item)

    return ProspectosPageResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get(
    "/jobs/recientes",
    response_model=JobsRecientesResponse,
    summary="Ultimos 10 jobs del sistema",
)
async def get_jobs_recientes(db: Session = Depends(get_db)) -> JobsRecientesResponse:
    total_jobs = db.query(func.count(ProcessingJob.id_job)).scalar() or 0
    jobs = (
        db.query(ProcessingJob)
        .order_by(ProcessingJob.created_at.desc())
        .limit(10)
        .all()
    )

    items = []
    for job in jobs:
        if job.is_prospecto and job.prospecto:
            nombre_sujeto = job.prospecto.nombre_completo
            tipo_sujeto = "prospecto"
        elif job.is_estudiante and job.estudiante:
            nombre_sujeto = job.estudiante.nombre_completo
            tipo_sujeto = "estudiante"
        else:
            nombre_sujeto = "Desconocido"
            tipo_sujeto = "desconocido"

        result = job.test_result
        test_code = result.template.code if result and result.template else None
        subject = result.template.subject if result and result.template else None
        semaforo = result.semaforo if result else None
        percentage = result.percentage if result else None
        completed_at_val = getattr(job, "completed_at", None)

        item = JobRecenteItemResponse(
            id_job=job.id_job,
            status=job.status,
            progress_percent=job.progress_percent,
            tipo_sujeto=tipo_sujeto,
            nombre_sujeto=nombre_sujeto,
            test_code=test_code,
            subject=subject,
            semaforo=semaforo,
            percentage=percentage,
            created_at=job.created_at,
            completed_at=completed_at_val,
            error_message=job.error_message,
        )
        items.append(item)

    return JobsRecientesResponse(
        total_jobs=total_jobs,
        jobs=items,
    )


@router.get(
    "/health",
    response_model=DashboardHealthResponse,
    summary="Health check del dashboard",
)
async def get_dashboard_health(db: Session = Depends(get_db)) -> DashboardHealthResponse:
    try:
        db.query(Prospecto).limit(1).all()
        return DashboardHealthResponse(
            status="ok",
            db_connected=True,
            message="Dashboard y BD funcionando correctamente",
        )
    except Exception as e:
        return DashboardHealthResponse(
            status="error",
            db_connected=False,
            message=f"Error de conexion: {str(e)}",
        )
