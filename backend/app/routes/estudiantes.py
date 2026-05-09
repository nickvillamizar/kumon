"""
app/routes/estudiantes.py
CRUD completo de estudiantes y horarios de clase.
"""
from __future__ import annotations
from uuid import UUID
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, model_validator

from config.database import get_db
from database.models import Student, Role, Usuario, ProcessingJob, TestResult

router = APIRouter(
    prefix="/api/v1/estudiantes",
    tags=["estudiantes"]
)

# ════════════════════════════════════════════════════════
# SCHEMAS
# ════════════════════════════════════════════════════════

class HorarioItem(BaseModel):
    dia: str
    franja: str

    model_config = {"from_attributes": True}


class EstudianteCreate(BaseModel):
    # Acepta tanto primer_nombre/primer_apellido como nombres/apellidos (alias frontend)
    primer_nombre: Optional[str] = None
    nombres: Optional[str] = None          # alias del frontend
    segundo_nombre: Optional[str] = None
    primer_apellido: Optional[str] = None
    apellidos: Optional[str] = None        # alias del frontend
    segundo_apellido: Optional[str] = None
    numero_documento: Optional[str] = None
    tipo_documento: Optional[str] = "CC"
    email: Optional[str] = None
    grado_escolar: Optional[str] = None
    institucion_origen: Optional[str] = None
    telefono_contacto: Optional[str] = None
    nombre_acudiente: Optional[str] = None
    telefono_acudiente: Optional[str] = None
    email_acudiente: Optional[str] = None
    relacion_acudiente: Optional[str] = None
    materias: Optional[List[str]] = []
    profesor_nombre: Optional[str] = None
    horario: Optional[List[HorarioItem]] = []

    @model_validator(mode='after')
    def resolve_names(self):
        # Si llega nombres en lugar de primer_nombre, dividir y asignar
        if not self.primer_nombre and self.nombres:
            parts = self.nombres.strip().split()
            self.primer_nombre = parts[0] if parts else self.nombres
            if len(parts) > 1 and not self.segundo_nombre:
                self.segundo_nombre = ' '.join(parts[1:])
        # Si llega apellidos en lugar de primer_apellido, dividir y asignar
        if not self.primer_apellido and self.apellidos:
            parts = self.apellidos.strip().split()
            self.primer_apellido = parts[0] if parts else self.apellidos
            if len(parts) > 1 and not self.segundo_apellido:
                self.segundo_apellido = ' '.join(parts[1:])
        # Garantizar valores por defecto
        if not self.primer_nombre:
            self.primer_nombre = 'Sin nombre'
        if not self.primer_apellido:
            self.primer_apellido = 'Sin apellido'
        return self


class EstudianteUpdate(BaseModel):
    primer_nombre: Optional[str] = None
    primer_apellido: Optional[str] = None
    segundo_apellido: Optional[str] = None
    email: Optional[str] = None
    grado_escolar: Optional[str] = None
    institucion_origen: Optional[str] = None
    telefono_contacto: Optional[str] = None
    nombre_acudiente: Optional[str] = None
    materias: Optional[List[str]] = None
    profesor_nombre: Optional[str] = None
    horario: Optional[List[HorarioItem]] = None


class EstudianteResponse(BaseModel):
    id_estudiante: UUID
    nombre_completo: str
    email: Optional[str]
    grado_escolar: Optional[str]
    institucion_origen: Optional[str]
    telefono_contacto: Optional[str]
    nombre_acudiente: Optional[str]
    telefono_acudiente: Optional[str]
    estado: str
    materias: List[str]
    profesor_nombre: Optional[str]
    horario: List[HorarioItem]
    total_diagnosticos: int
    ultimo_semaforo: Optional[str]

    model_config = {"from_attributes": True}


class EstudiantesListResponse(BaseModel):
    total: int
    items: List[EstudianteResponse]


class HorarioUpdate(BaseModel):
    horario: List[HorarioItem]


# ════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════

def _build_response(estudiante: Student, db: Session) -> EstudianteResponse:
    """Construye la respuesta enriquecida para un estudiante."""
    total_diag = (
        db.query(func.count(ProcessingJob.id_job))
        .filter(ProcessingJob.id_estudiante == estudiante.id_estudiante)
        .scalar() or 0
    )
    ultimo_result = (
        db.query(TestResult)
        .filter(TestResult.id_estudiante == estudiante.id_estudiante)
        .order_by(TestResult.created_at.desc())
        .first()
    )
    ultimo_semaforo = ultimo_result.semaforo if ultimo_result else None

    import json
    extra = {}
    if estudiante.direccion and estudiante.direccion.startswith('{'):
        try:
            extra = json.loads(estudiante.direccion)
        except Exception:
            extra = {}

    materias = extra.get('materias', [])
    profesor_nombre = extra.get('profesor_nombre', None)
    horario_raw = extra.get('horario', [])
    horario = [HorarioItem(**h) for h in horario_raw]

    return EstudianteResponse(
        id_estudiante=estudiante.id_estudiante,
        nombre_completo=estudiante.nombre_completo,
        email=estudiante.email,
        grado_escolar=estudiante.grado_escolar,
        institucion_origen=estudiante.institucion_origen,
        telefono_contacto=estudiante.telefono_contacto,
        nombre_acudiente=estudiante.nombre_acudiente,
        telefono_acudiente=estudiante.telefono_acudiente,
        estado=estudiante.estado,
        materias=materias,
        profesor_nombre=profesor_nombre,
        horario=horario,
        total_diagnosticos=total_diag,
        ultimo_semaforo=ultimo_semaforo,
    )


# ════════════════════════════════════════════════════════
# GET /api/v1/estudiantes
# ════════════════════════════════════════════════════════

@router.get("/", response_model=EstudiantesListResponse, summary="Listar estudiantes")
async def listar_estudiantes(
    profesor_nombre: Optional[str] = None,
    estado: Optional[str] = "activo",
    db: Session = Depends(get_db),
) -> EstudiantesListResponse:
    query = db.query(Student)
    if estado:
        query = query.filter(Student.estado == estado)
    estudiantes = query.order_by(Student.primer_apellido).all()
    if profesor_nombre:
        import json
        filtrados = []
        for e in estudiantes:
            extra = {}
            if e.direccion and e.direccion.startswith('{'):
                try:
                    extra = json.loads(e.direccion)
                except Exception:
                    pass
            if extra.get('profesor_nombre') == profesor_nombre:
                filtrados.append(e)
        estudiantes = filtrados
    items = [_build_response(e, db) for e in estudiantes]
    return EstudiantesListResponse(total=len(items), items=items)


# ════════════════════════════════════════════════════════
# GET /api/v1/estudiantes/{id}
# ════════════════════════════════════════════════════════

@router.get("/{id_estudiante}", response_model=EstudianteResponse, summary="Detalle estudiante")
async def get_estudiante(
    id_estudiante: UUID,
    db: Session = Depends(get_db),
) -> EstudianteResponse:
    e = db.query(Student).filter(Student.id_estudiante == id_estudiante).first()
    if not e:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return _build_response(e, db)


# ════════════════════════════════════════════════════════
# POST /api/v1/estudiantes
# ════════════════════════════════════════════════════════

@router.post("/", response_model=EstudianteResponse, status_code=201, summary="Crear estudiante")
async def crear_estudiante(
    body: EstudianteCreate,
    db: Session = Depends(get_db),
) -> EstudianteResponse:
    import json
    extra = {
        'materias': body.materias,
        'profesor_nombre': body.profesor_nombre,
        'horario': [h.model_dump() for h in (body.horario or [])],
    }
    nuevo = Student(
        primer_nombre=body.primer_nombre,
        segundo_nombre=body.segundo_nombre,
        primer_apellido=body.primer_apellido,
        segundo_apellido=body.segundo_apellido,
        numero_documento=body.numero_documento,
        tipo_documento=body.tipo_documento or "CC",
        email=body.email,
        grado_escolar=body.grado_escolar,
        institucion_origen=body.institucion_origen,
        telefono_contacto=body.telefono_contacto,
        nombre_acudiente=body.nombre_acudiente,
        telefono_acudiente=body.telefono_acudiente,
        email_acudiente=body.email_acudiente,
        relacion_acudiente=body.relacion_acudiente,
        direccion=json.dumps(extra, ensure_ascii=False),
        estado="activo",
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return _build_response(nuevo, db)


# ════════════════════════════════════════════════════════
# PUT /api/v1/estudiantes/{id}
# ════════════════════════════════════════════════════════

@router.put("/{id_estudiante}", response_model=EstudianteResponse, summary="Actualizar estudiante")
async def actualizar_estudiante(
    id_estudiante: UUID,
    body: EstudianteUpdate,
    db: Session = Depends(get_db),
) -> EstudianteResponse:
    import json
    e = db.query(Student).filter(Student.id_estudiante == id_estudiante).first()
    if not e:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    extra = {}
    if e.direccion and e.direccion.startswith('{'):
        try:
            extra = json.loads(e.direccion)
        except Exception:
            pass
    if body.primer_nombre is not None:
        e.primer_nombre = body.primer_nombre
    if body.primer_apellido is not None:
        e.primer_apellido = body.primer_apellido
    if body.segundo_apellido is not None:
        e.segundo_apellido = body.segundo_apellido
    if body.email is not None:
        e.email = body.email
    if body.grado_escolar is not None:
        e.grado_escolar = body.grado_escolar
    if body.institucion_origen is not None:
        e.institucion_origen = body.institucion_origen
    if body.telefono_contacto is not None:
        e.telefono_contacto = body.telefono_contacto
    if body.nombre_acudiente is not None:
        e.nombre_acudiente = body.nombre_acudiente
    if body.materias is not None:
        extra['materias'] = body.materias
    if body.profesor_nombre is not None:
        extra['profesor_nombre'] = body.profesor_nombre
    if body.horario is not None:
        extra['horario'] = [h.model_dump() for h in body.horario]
    e.direccion = json.dumps(extra, ensure_ascii=False)
    db.commit()
    db.refresh(e)
    return _build_response(e, db)


# ════════════════════════════════════════════════════════
# DELETE /api/v1/estudiantes/{id}
# ════════════════════════════════════════════════════════

@router.delete("/{id_estudiante}", status_code=204, summary="Desactivar estudiante")
async def desactivar_estudiante(
    id_estudiante: UUID,
    db: Session = Depends(get_db),
):
    e = db.query(Student).filter(Student.id_estudiante == id_estudiante).first()
    if not e:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    e.estado = "inactivo"
    db.commit()
    return None


# ════════════════════════════════════════════════════════
# PUT /api/v1/estudiantes/{id}/horario
# ════════════════════════════════════════════════════════

@router.put("/{id_estudiante}/horario", response_model=EstudianteResponse, summary="Actualizar horario")
async def actualizar_horario(
    id_estudiante: UUID,
    body: HorarioUpdate,
    db: Session = Depends(get_db),
) -> EstudianteResponse:
    import json
    e = db.query(Student).filter(Student.id_estudiante == id_estudiante).first()
    if not e:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    extra = {}
    if e.direccion and e.direccion.startswith('{'):
        try:
            extra = json.loads(e.direccion)
        except Exception:
            pass
    extra['horario'] = [h.model_dump() for h in body.horario]
    e.direccion = json.dumps(extra, ensure_ascii=False)
    db.commit()
    db.refresh(e)
    return _build_response(e, db)
