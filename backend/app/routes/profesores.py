"""
app/routes/profesores.py
CRUD completo de profesores (usuarios con rol=profesor).
"""
from __future__ import annotations
from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel

from config.database import get_db
from database.models import Usuario, Role, Student, ProcessingJob

router = APIRouter(prefix="/api/v1/profesores", tags=["profesores"])


# ════════════════════════════════════════════════════════
# SCHEMAS
# ════════════════════════════════════════════════════════

class ProfesorCreate(BaseModel):
    nombre_completo: str
    email: str
    password: str = "prof123"
    materias: Optional[List[str]] = []


class ProfesorUpdate(BaseModel):
    nombre_completo: Optional[str] = None
    email: Optional[str] = None
    materias: Optional[List[str]] = None
    activo: Optional[bool] = None


class ProfesorResponse(BaseModel):
    id_usuario: UUID
    nombre_completo: str
    email: str
    materias: List[str]
    activo: bool
    total_estudiantes: int

    model_config = {"from_attributes": True}


class ProfesoresListResponse(BaseModel):
    total: int
    items: List[ProfesorResponse]


# ════════════════════════════════════════════════════════
# HELPER
# ════════════════════════════════════════════════════════

def _get_rol_profesor(db: Session) -> Role:
    rol = db.query(Role).filter(Role.nombre_rol == "profesor").first()
    if not rol:
        raise HTTPException(status_code=500, detail="Rol 'profesor' no existe en BD")
    return rol


def _count_estudiantes(nombre_completo: str, db: Session) -> int:
    import json
    estudiantes = db.query(Student).filter(Student.estado == "activo").all()
    count = 0
    for e in estudiantes:
        extra = {}
        if e.direccion and e.direccion.startswith('{'):
            try:
                extra = json.loads(e.direccion)
            except Exception:
                pass
        if extra.get('profesor_nombre') == nombre_completo:
            count += 1
    return count


def _build_response(usuario: Usuario, db: Session) -> ProfesorResponse:
    import json
    extra = {}
    # Materias guardadas en el campo de permisos del rol (JSONB) o en el email como convención
    # Usamos un campo auxiliar: si el email contiene notas extras las parseamos
    # Alternativa: guardamos materias en permisos del usuario mismo
    if usuario.rol and usuario.rol.permisos:
        permisos = usuario.rol.permisos if isinstance(usuario.rol.permisos, dict) else {}
        extra = permisos

    # Materias por profesor guardadas en el primer_nombre como JSON (hack temporal)
    # En realidad guardamos en segundo_nombre el JSON de materias
    materias = []
    if usuario.segundo_nombre and usuario.segundo_nombre.startswith('['):
        try:
            materias = json.loads(usuario.segundo_nombre)
        except Exception:
            pass

    nombre_completo = f"{usuario.primer_nombre} {usuario.primer_apellido}"
    if usuario.segundo_apellido:
        nombre_completo = f"{usuario.primer_nombre} {usuario.segundo_apellido}"

    total_est = _count_estudiantes(nombre_completo, db)

    return ProfesorResponse(
        id_usuario=usuario.id_usuario,
        nombre_completo=nombre_completo,
        email=usuario.email,
        materias=materias,
        activo=usuario.activo,
        total_estudiantes=total_est,
    )


# ════════════════════════════════════════════════════════
# GET /api/v1/profesores
# ════════════════════════════════════════════════════════
@router.get("/", response_model=ProfesoresListResponse, summary="Listar profesores")
async def listar_profesores(db: Session = Depends(get_db)) -> ProfesoresListResponse:
    rol = db.query(Role).filter(Role.nombre_rol == "profesor").first()
    if not rol:
        return ProfesoresListResponse(total=0, items=[])
    profesores = (
        db.query(Usuario)
        .filter(Usuario.id_rol == rol.id_rol, Usuario.deleted_at.is_(None))
        .order_by(Usuario.primer_apellido)
        .all()
    )
    items = [_build_response(p, db) for p in profesores]
    return ProfesoresListResponse(total=len(items), items=items)


# ════════════════════════════════════════════════════════
# POST /api/v1/profesores
# ════════════════════════════════════════════════════════
@router.post("/", response_model=ProfesorResponse, status_code=201, summary="Crear profesor")
async def crear_profesor(
    body: ProfesorCreate,
    db: Session = Depends(get_db),
) -> ProfesorResponse:
    import json
    import hashlib

    rol = _get_rol_profesor(db)

    # Separar nombre en partes
    partes = body.nombre_completo.strip().split()
    primer_nombre = partes[0] if len(partes) > 0 else body.nombre_completo
    primer_apellido = partes[-1] if len(partes) > 1 else ""

    # Hash de password simple
    password_hash = hashlib.sha256(body.password.encode()).hexdigest()

    nuevo = Usuario(
        id_rol=rol.id_rol,
        primer_nombre=primer_nombre,
        primer_apellido=primer_apellido,
        # Guardamos materias en segundo_nombre como JSON (campo existente disponible)
        segundo_nombre=json.dumps(body.materias, ensure_ascii=False),
        # Guardamos nombre completo en segundo_apellido para facilitar búsquedas
        segundo_apellido=body.nombre_completo,
        email=body.email,
        password_hash=password_hash,
        activo=True,
        email_verificado=True,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return _build_response(nuevo, db)


# ════════════════════════════════════════════════════════
# PUT /api/v1/profesores/{id}
# ════════════════════════════════════════════════════════
@router.put("/{id_usuario}", response_model=ProfesorResponse, summary="Actualizar profesor")
async def actualizar_profesor(
    id_usuario: UUID,
    body: ProfesorUpdate,
    db: Session = Depends(get_db),
) -> ProfesorResponse:
    import json
    p = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not p:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")

    if body.nombre_completo is not None:
        partes = body.nombre_completo.strip().split()
        p.primer_nombre = partes[0] if len(partes) > 0 else body.nombre_completo
        p.primer_apellido = partes[-1] if len(partes) > 1 else ""
        p.segundo_apellido = body.nombre_completo
    if body.email is not None:
        p.email = body.email
    if body.materias is not None:
        p.segundo_nombre = json.dumps(body.materias, ensure_ascii=False)
    if body.activo is not None:
        p.activo = body.activo

    db.commit()
    db.refresh(p)
    return _build_response(p, db)


# ════════════════════════════════════════════════════════
# DELETE /api/v1/profesores/{id}
# ════════════════════════════════════════════════════════
@router.delete("/{id_usuario}", status_code=204, summary="Desactivar profesor")
async def desactivar_profesor(
    id_usuario: UUID,
    db: Session = Depends(get_db),
):
    p = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if not p:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    p.activo = False
    db.commit()
    return None
