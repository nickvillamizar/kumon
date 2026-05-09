"""
app/schemas/dashboard.py
══════════════════════════════════════════════════════════════════
Schemas para los endpoints del panel administrativo.
Usado en:
  - GET /api/v1/dashboard/stats
  - GET /api/v1/dashboard/prospectos
  - GET /api/v1/dashboard/jobs/recientes
══════════════════════════════════════════════════════════════════
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, UUID4


# ══════════════════════════════════════════════════════════════════
# STATS — Estadísticas generales del dashboard
# ══════════════════════════════════════════════════════════════════

class DashboardStatsResponse(BaseModel):
    """
    Estadísticas agregadas para mostrar en los KPI del panel.
    """

    # ── Totales ────────────────────────────────────────────────
    total_estudiantes: int = Field(description="Total de estudiantes en BD")
    total_profesores: int = Field(description="Total de profesores")
    clases_hoy: int = Field(description="Clases programadas hoy (aproximado)")
    boletines_generados: int = Field(description="Boletines PDF generados")

    # ── Distribución por semáforo ──────────────────────────────
    semaforo_verde: int = Field(description="Estudiantes en nivel verde (avanzado)")
    semaforo_amarillo: int = Field(description="Estudiantes en nivel amarillo (intermedio)")
    semaforo_rojo: int = Field(description="Estudiantes en nivel rojo (refuerzo)")

    # ── Distribución por materia ───────────────────────────────
    materias_matematicas: int = Field(description="Total de estudiantes en MAT")
    materias_espanol: int = Field(description="Total de estudiantes en ESP")
    materias_ingles: int = Field(description="Total de estudiantes en ING")

    # ── Jobs recientes ────────────────────────────────────────
    jobs_en_cola: int = Field(description="Jobs queued")
    jobs_procesando: int = Field(description="Jobs processing")
    jobs_completados_hoy: int = Field(description="Jobs completados hoy")

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════
# PROSPECTO — Item en lista de prospectos
# ══════════════════════════════════════════════════════════════════

class ProspectoItemResponse(BaseModel):
    """
    Prospecto individual con su último resultado y semáforo.
    Usado en GET /api/v1/dashboard/prospectos.
    """

    id_prospecto: UUID4 = Field(description="ID único del prospecto")
    nombre_completo: str = Field(description="Nombre completo")
    grado_escolar: Optional[str] = Field(default=None, description="Grado escolar")
    nombre_escuela: Optional[str] = Field(default=None, description="Nombre escuela")
    fecha_prueba: Optional[str] = Field(default=None, description="Fecha de prueba (YYYY-MM-DD)")

    # ── Último resultado ───────────────────────────────────────
    test_code: Optional[str] = Field(default=None, description="Código del test (MAT-A1, etc)")
    subject: Optional[str] = Field(default=None, description="Materia: matematicas, espanol, ingles")
    semaforo: Optional[str] = Field(default=None, description="verde | amarillo | rojo | null")
    percentage: Optional[Decimal] = Field(default=None, description="Porcentaje del test (0-100)")
    fecha_resultado: Optional[datetime] = Field(default=None, description="Timestamp del último resultado")

    # ── Acciones ───────────────────────────────────────────────
    tiene_boletin: bool = Field(default=False, description="True si ya existe un boletín")
    job_id: Optional[str] = Field(default=None, description="ID del último job (si aplica)")

    model_config = {"from_attributes": True}


class ProspectosPageResponse(BaseModel):
    """
    Respuesta paginada de lista de prospectos.
    """

    total: int = Field(description="Total de prospectos en BD")
    page: int = Field(description="Página actual (1-indexed)")
    page_size: int = Field(description="Items por página")
    items: List[ProspectoItemResponse] = Field(description="Prospectos en esta página")

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════
# JOBS RECIENTES — Últimos jobs del pipeline
# ══════════════════════════════════════════════════════════════════

class JobRecenteItemResponse(BaseModel):
    """
    Job reciente con información resumida.
    Usado en GET /api/v1/dashboard/jobs/recientes.
    """

    id_job: UUID4 = Field(description="ID del job")
    status: str = Field(description="queued | processing | done | error | manual_review")
    progress_percent: int = Field(ge=0, le=100, description="Progreso 0-100")

    # ── Sujeto ────────────────────────────────────────────────
    tipo_sujeto: str = Field(description="prospecto | estudiante")
    nombre_sujeto: str = Field(description="Nombre del prospecto o estudiante")

    # ── Test ───────────────────────────────────────────────────
    test_code: Optional[str] = Field(default=None, description="MAT-A1, ESP-02, etc")
    subject: Optional[str] = Field(default=None, description="matematicas, espanol, ingles")

    # ── Resultado ──────────────────────────────────────────────
    semaforo: Optional[str] = Field(default=None, description="verde | amarillo | rojo | null")
    percentage: Optional[Decimal] = Field(default=None, description="% del test (0-100)")

    # ── Timestamps ────────────────────────────────────────────
    created_at: datetime = Field(description="Cuándo se subió el video")
    completed_at: Optional[datetime] = Field(default=None, description="Cuándo finalizó el procesamiento")

    # ── Error ──────────────────────────────────────────────────
    error_message: Optional[str] = Field(default=None, description="Mensaje de error si status=error")

    model_config = {"from_attributes": True}


class JobsRecientesResponse(BaseModel):
    """
    Últimos 10 jobs del sistema.
    """

    total_jobs: int = Field(description="Total de jobs en BD")
    jobs: List[JobRecenteItemResponse] = Field(description="Últimos 10 jobs")

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════
# HEALTH CHECK — simple
# ══════════════════════════════════════════════════════════════════

class DashboardHealthResponse(BaseModel):
    """
    Health check del dashboard: verifica que BD esté accesible.
    """

    status: str = Field(description="ok | error")
    db_connected: bool = Field(description="True si PostgreSQL responde")
    message: Optional[str] = Field(default=None)

    model_config = {"from_attributes": True}
