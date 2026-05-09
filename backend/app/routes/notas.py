"""
app/routes/notas.py
CRUD de notas de clase del profesor.
"""
from __future__ import annotations
from uuid import UUID
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from config.database import get_db
from database.models import TestResult, Student, Prospecto

router = APIRouter(prefix="/api/v1/notas", tags=["notas"])

# ════════════════════════════════════════════════════════
# SCHEMAS
# ════════════════════════════════════════════════════════

class NotaCreate(BaseModel):
    id_result: UUID
    profesor_nombre: str
    observacion: str
    estrellas: int = 5

class NotaResponse(BaseModel):
    id_nota: str
    fecha: str
    estudiante: str
    materia: Optional[str]
    profesor_nombre: str
    observacion: str
    estrellas: int

    model_config = {"from_attributes": True}

class NotasListResponse(BaseModel):
    total: int
    items: List[NotaResponse]

class NotaPorEstudianteCreate(BaseModel):
    id_estudiante: str   # UUID como string
    materia: str
    estrellas: int = 3
    observacion: str

# ════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════

def _build_nota_response(r: TestResult, nota: dict, db: Session) -> NotaResponse:
    nombre_estudiante = "Desconocido"
    if r.id_estudiante:
        est = db.query(Student).filter(
            Student.id_estudiante == r.id_estudiante
        ).first()
        if est:
            nombre_estudiante = est.nombre_completo
    elif r.id_prospecto:
        prosp = db.query(Prospecto).filter(
            Prospecto.id_prospecto == r.id_prospecto
        ).first()
        if prosp:
            nombre_estudiante = prosp.nombre_completo

    materia = r.template.subject if r.template else None

    return NotaResponse(
        id_nota=str(r.id_result) + "_" + str(nota["idx"]),
        fecha=nota["fecha"],
        estudiante=nombre_estudiante,
        materia=nota.get("materia") or materia,
        profesor_nombre=nota["profesor_nombre"],
        observacion=nota["observacion"],
        estrellas=nota["estrellas"],
    )

# ════════════════════════════════════════════════════════
# GET /api/v1/notas
# ════════════════════════════════════════════════════════
@router.get("/", response_model=NotasListResponse, summary="Listar notas de clase")
def listar_notas(
    profesor_nombre: Optional[str] = None,
    db: Session = Depends(get_db),
) -> NotasListResponse:
    resultados = db.query(TestResult).filter(
        TestResult.raw_ocr_data.isnot(None)
    ).all()

    items = []
    for r in resultados:
        raw = r.raw_ocr_data or {}
        notas = raw.get("notas_profesor", [])
        if not isinstance(notas, list):
            continue
        for nota in notas:
            if not isinstance(nota, dict):
                continue
            if profesor_nombre and nota.get("profesor_nombre") != profesor_nombre:
                continue
            try:
                items.append(_build_nota_response(r, nota, db))
            except Exception:
                continue

    return NotasListResponse(total=len(items), items=items)

# ════════════════════════════════════════════════════════
# POST /api/v1/notas
# ════════════════════════════════════════════════════════
@router.post("/", response_model=NotaResponse, status_code=201, summary="Crear nota via id_result")
def crear_nota(
    body: NotaCreate,
    db: Session = Depends(get_db),
) -> NotaResponse:
    r = db.query(TestResult).filter(TestResult.id_result == body.id_result).first()
    if not r:
        raise HTTPException(status_code=404, detail="TestResult no encontrado")

    raw = r.raw_ocr_data or {}
    notas = raw.get("notas_profesor", [])
    if not isinstance(notas, list):
        notas = []

    nueva_nota = {
        "idx": len(notas),
        "fecha": date.today().isoformat(),
        "materia": None,
        "profesor_nombre": body.profesor_nombre,
        "observacion": body.observacion,
        "estrellas": body.estrellas,
    }
    notas.append(nueva_nota)
    raw["notas_profesor"] = notas
    r.raw_ocr_data = raw
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(r, "raw_ocr_data")
    db.commit()
    return _build_nota_response(r, nueva_nota, db)

# ════════════════════════════════════════════════════════
# POST /api/v1/notas/por-estudiante
# Crear nota directamente con UUID del estudiante
# ════════════════════════════════════════════════════════
@router.post("/por-estudiante", status_code=201, summary="Crear nota por id_estudiante (UUID)")
def crear_nota_por_estudiante(
    body: NotaPorEstudianteCreate,
    db: Session = Depends(get_db),
):
    # Convertir string a UUID
    try:
        estudiante_uuid = UUID(body.id_estudiante)
    except ValueError:
        raise HTTPException(status_code=422, detail="id_estudiante debe ser un UUID valido")

    # Verificar que el estudiante existe
    est = db.query(Student).filter(Student.id_estudiante == estudiante_uuid).first()
    if not est:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    # Buscar el TestResult mas reciente del estudiante
    tr = db.query(TestResult).filter(
        TestResult.id_estudiante == estudiante_uuid
    ).order_by(TestResult.created_at.desc()).first()

    if not tr:
        raise HTTPException(
            status_code=404,
            detail="Este estudiante no tiene diagnosticos aun. Crea un diagnostico primero."
        )

    # Leer notas existentes
    raw = tr.raw_ocr_data or {}
    notas = raw.get("notas_profesor", [])
    if not isinstance(notas, list):
        notas = []

    nueva_nota = {
        "idx": len(notas),
        "fecha": date.today().isoformat(),
        "materia": body.materia,
        "estrellas": body.estrellas,
        "observacion": body.observacion,
        "profesor_nombre": "Profesor"
    }
    notas.append(nueva_nota)
    raw["notas_profesor"] = notas
    tr.raw_ocr_data = raw
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(tr, "raw_ocr_data")
    db.commit()

    return {
        "id_nota": str(tr.id_result) + "_" + str(nueva_nota["idx"]),
        "fecha": nueva_nota["fecha"],
        "estudiante": est.nombre_completo,
        "materia": body.materia,
        "estrellas": body.estrellas,
        "observacion": body.observacion,
        "profesor_nombre": "Profesor"
    }
