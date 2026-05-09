"""
app/routes/notas.py
CRUD de notas de clase (observaciones del profesor).
Se almacenan en ObservacionCualitativa que ya existe en el modelo.
"""
from __future__ import annotations
from uuid import UUID
from datetime import datetime
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


# ════════════════════════════════════════════════════════
# GET /api/v1/notas
# Devuelve notas desde el campo recommendation de TestResult
# y observaciones en el campo raw_ocr_data["notas_profesor"]
# ════════════════════════════════════════════════════════

@router.get("/", response_model=NotasListResponse, summary="Listar notas de clase")
async def listar_notas(
    profesor_nombre: Optional[str] = None,
    db: Session = Depends(get_db),
) -> NotasListResponse:
    """
    Devuelve notas de clase guardadas en TestResult.raw_ocr_data["notas_profesor"].
    Si no hay notas aún, retorna lista vacía.
    """
    resultados = db.query(TestResult).order_by(TestResult.created_at.desc()).all()

    items = []
    for r in resultados:
        # Extraer notas guardadas por el profesor en el JSON
        notas_raw = []
        if r.raw_ocr_data and isinstance(r.raw_ocr_data, dict):
            notas_raw = r.raw_ocr_data.get("notas_profesor", [])

        for nota in notas_raw:
            if profesor_nombre and nota.get("profesor_nombre") != profesor_nombre:
                continue

            # Obtener nombre del estudiante
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

            # Materia desde template
            materia = None
            if r.template:
                materia = r.template.subject

            items.append(NotaResponse(
                id_nota=str(r.id_result) + "_" + str(nota.get("idx", 0)),
                fecha=nota.get("fecha", r.created_at.strftime("%Y-%m-%d")),
                estudiante=nombre_estudiante,
                materia=materia,
                profesor_nombre=nota.get("profesor_nombre", ""),
                observacion=nota.get("observacion", ""),
                estrellas=nota.get("estrellas", 5),
            ))

    return NotasListResponse(total=len(items), items=items)


# ════════════════════════════════════════════════════════
# POST /api/v1/notas
# Guarda una nota en raw_ocr_data["notas_profesor"] del TestResult
# ════════════════════════════════════════════════════════

@router.post("/", response_model=NotaResponse, status_code=201, summary="Crear nota de clase")
async def crear_nota(
    body: NotaCreate,
    db: Session = Depends(get_db),
) -> NotaResponse:
    """
    Agrega una nota de clase al TestResult especificado.
    Las notas se guardan en raw_ocr_data["notas_profesor"] como lista.
    """
    r = db.query(TestResult).filter(TestResult.id_result == body.id_result).first()
    if not r:
        raise HTTPException(status_code=404, detail="Resultado de test no encontrado")

    # Inicializar raw_ocr_data si es None
    if r.raw_ocr_data is None:
        r.raw_ocr_data = {}

    notas_existentes = r.raw_ocr_data.get("notas_profesor", [])
    nueva_nota = {
        "idx": len(notas_existentes),
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "profesor_nombre": body.profesor_nombre,
        "observacion": body.observacion,
        "estrellas": body.estrellas,
    }
    notas_existentes.append(nueva_nota)

    # Actualizar el campo usando merge para forzar el update del JSONB
    from sqlalchemy.orm.attributes import flag_modified
    r.raw_ocr_data["notas_profesor"] = notas_existentes
    flag_modified(r, "raw_ocr_data")
    db.commit()
    db.refresh(r)

    # Obtener nombre del estudiante
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
        id_nota=str(r.id_result) + "_" + str(nueva_nota["idx"]),
        fecha=nueva_nota["fecha"],
        estudiante=nombre_estudiante,
        materia=materia,
        profesor_nombre=nueva_nota["profesor_nombre"],
        observacion=nueva_nota["observacion"],
        estrellas=nueva_nota["estrellas"],
    )
