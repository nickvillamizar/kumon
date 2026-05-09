"""
app/routes/horarios.py
CRUD de horarios de clase para el EduPanel.
"""
from __future__ import annotations
from uuid import UUID, uuid4
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from config.database import get_db
from database.models import Student, Usuario

router = APIRouter(prefix="/api/v1/horarios", tags=["horarios"])

# ============================================================
# SCHEMAS
# ============================================================

class HorarioCreate(BaseModel):
    id_estudiante: str
    id_profesor: str
    dia: str
    hora_inicio: str
    hora_fin: str
    materia: Optional[str] = None

    model_config = {"from_attributes": True}


class HorarioResponse(BaseModel):
    id_horario: str
    id_estudiante: str
    id_profesor: str
    nombre_estudiante: Optional[str] = None
    nombre_profesor: Optional[str] = None
    dia: str
    hora_inicio: str
    hora_fin: str
    materia: Optional[str] = None

    model_config = {"from_attributes": True}


class HorariosListResponse(BaseModel):
    total: int
    items: List[HorarioResponse]


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/", response_model=HorariosListResponse, summary="Listar todos los horarios")
async def listar_horarios(db: Session = Depends(get_db)) -> HorariosListResponse:
    estudiantes = db.query(Student).filter(Student.estado == "activo").all()
    items: List[HorarioResponse] = []
    for est in estudiantes:
        if est.horario:
            for slot in (est.horario if isinstance(est.horario, list) else []):
                prof_nombre = est.profesor_nombre or ""
                items.append(HorarioResponse(
                    id_horario=f"{est.id_estudiante}-{slot.get('dia','')}-{slot.get('franja','')}",
                    id_estudiante=str(est.id_estudiante),
                    id_profesor=str(est.id_profesor) if hasattr(est, 'id_profesor') and est.id_profesor else "",
                    nombre_estudiante=f"{est.primer_nombre} {est.primer_apellido}",
                    nombre_profesor=prof_nombre,
                    dia=slot.get("dia", ""),
                    hora_inicio=slot.get("franja", ""),
                    hora_fin=slot.get("franja_fin", ""),
                    materia=slot.get("materia", ""),
                ))
    return HorariosListResponse(total=len(items), items=items)


@router.post("/", response_model=HorarioResponse, status_code=201, summary="Crear clase en horario")
async def crear_horario(body: HorarioCreate, db: Session = Depends(get_db)) -> HorarioResponse:
    try:
        est_uuid = UUID(body.id_estudiante)
    except ValueError:
        raise HTTPException(status_code=400, detail="id_estudiante invalido")

    est = db.query(Student).filter(Student.id_estudiante == est_uuid).first()
    if not est:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    horario_actual = est.horario if isinstance(est.horario, list) else []
    nuevo_slot = {
        "dia": body.dia,
        "franja": body.hora_inicio,
        "franja_fin": body.hora_fin,
        "materia": body.materia or "",
    }
    horario_actual.append(nuevo_slot)
    est.horario = horario_actual

    # Buscar nombre del profesor
    prof_nombre = ""
    try:
        prof_uuid = UUID(body.id_profesor)
        prof = db.query(Usuario).filter(Usuario.id_usuario == prof_uuid).first()
        if prof:
            prof_nombre = prof.nombre_completo or ""
            est.profesor_nombre = prof_nombre
    except Exception:
        pass

    db.commit()
    db.refresh(est)

    id_horario = f"{est.id_estudiante}-{body.dia}-{body.hora_inicio}"
    return HorarioResponse(
        id_horario=id_horario,
        id_estudiante=str(est.id_estudiante),
        id_profesor=body.id_profesor,
        nombre_estudiante=f"{est.primer_nombre} {est.primer_apellido}",
        nombre_profesor=prof_nombre,
        dia=body.dia,
        hora_inicio=body.hora_inicio,
        hora_fin=body.hora_fin,
        materia=body.materia,
    )


@router.delete("/{id_horario}", status_code=204, summary="Eliminar clase del horario")
async def eliminar_horario(id_horario: str, db: Session = Depends(get_db)):
    # id_horario format: {id_estudiante}-{dia}-{hora_inicio}
    parts = id_horario.split("-", 1)
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="id_horario invalido")
    try:
        est_uuid = UUID(parts[0])
    except ValueError:
        raise HTTPException(status_code=400, detail="UUID invalido en id_horario")

    est = db.query(Student).filter(Student.id_estudiante == est_uuid).first()
    if not est:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    if isinstance(est.horario, list):
        remaining = [s for s in est.horario if not id_horario.endswith(f"{s.get('dia','')}-{s.get('franja','')}" )]
        est.horario = remaining
        db.commit()
    return None
