"""
app/routes/horarios.py
CRUD de horarios de clase - usa modelo ClaseHorario con tabla admin.clases_horario.
"""
from __future__ import annotations
from uuid import UUID
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from config.database import get_db
from database.models import Student, Usuario
from database.models_horario import ClaseHorario

router = APIRouter(prefix="/api/v1/horarios", tags=["horarios"])


# ── Schemas ──────────────────────────────────────────────────
class HorarioCreate(BaseModel):
    id_estudiante: str
    id_profesor: Optional[str] = None
    dia: str
    hora_inicio: str
    hora_fin: str
    materia: Optional[str] = None


class HorarioResponse(BaseModel):
    id_horario: str
    id_estudiante: str
    id_profesor: Optional[str] = None
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


# ── Helpers ──────────────────────────────────────────────────
def _nombre_estudiante(est: Student) -> str:
    partes = [est.primer_nombre or "", est.primer_apellido or ""]
    return " ".join(p for p in partes if p).strip()


def _nombre_profesor(prof: Usuario) -> str:
    partes = [prof.primer_nombre or "", prof.primer_apellido or ""]
    return " ".join(p for p in partes if p).strip()


def _to_response(h: ClaseHorario) -> HorarioResponse:
    est_nombre = _nombre_estudiante(h.estudiante) if h.estudiante else ""
    prof_nombre = _nombre_profesor(h.profesor) if h.profesor else ""
    return HorarioResponse(
        id_horario=str(h.id_horario),
        id_estudiante=str(h.id_estudiante),
        id_profesor=str(h.id_profesor) if h.id_profesor else None,
        nombre_estudiante=est_nombre,
        nombre_profesor=prof_nombre,
        dia=h.dia,
        hora_inicio=h.hora_inicio,
        hora_fin=h.hora_fin,
        materia=h.materia,
    )


# ── Endpoints ────────────────────────────────────────────────
@router.get("/", response_model=HorariosListResponse, summary="Listar horarios")
async def listar_horarios(db: Session = Depends(get_db)) -> HorariosListResponse:
    registros = db.query(ClaseHorario).filter(ClaseHorario.activo == True).all()
    items = [_to_response(h) for h in registros]
    return HorariosListResponse(total=len(items), items=items)


@router.post("/", response_model=HorarioResponse, status_code=201, summary="Crear clase")
async def crear_horario(body: HorarioCreate, db: Session = Depends(get_db)) -> HorarioResponse:
    try:
        est_uuid = UUID(body.id_estudiante)
    except ValueError:
        raise HTTPException(status_code=400, detail="id_estudiante invalido")

    est = db.query(Student).filter(Student.id_estudiante == est_uuid).first()
    if not est:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    prof_uuid = None
    if body.id_profesor:
        try:
            prof_uuid = UUID(body.id_profesor)
        except ValueError:
            pass

    nueva = ClaseHorario(
        id_estudiante=est_uuid,
        id_profesor=prof_uuid,
        dia=body.dia,
        hora_inicio=body.hora_inicio,
        hora_fin=body.hora_fin,
        materia=body.materia,
        activo=True,
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return _to_response(nueva)


@router.delete("/{id_horario}", status_code=204, summary="Eliminar clase del horario")
async def eliminar_horario(id_horario: str, db: Session = Depends(get_db)):
    try:
        h_uuid = UUID(id_horario)
    except ValueError:
        raise HTTPException(status_code=400, detail="id_horario invalido")

    h = db.query(ClaseHorario).filter(ClaseHorario.id_horario == h_uuid).first()
    if not h:
        raise HTTPException(status_code=404, detail="Horario no encontrado")

    h.activo = False
    db.commit()
    return None
