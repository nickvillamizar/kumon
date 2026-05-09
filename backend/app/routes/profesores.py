"""
app/routes/profesores.py
CRUD completo de profesores (usuarios con rol=profesor).
"""
from __future__ import annotations
from uuid import UUID
from typing import List, Optional
import hashlib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel, model_validator

from config.database import get_db
from database.models import Usuario, Role, Student, ProcessingJob

router = APIRouter(prefix="/api/v1/profesores", tags=["profesores"])

# =============================================================
# SCHEMAS
# =============================================================

class ProfesorCreate(BaseModel):
    nombre_completo: Optional[str] = None
    nombre: Optional[str] = None   # alias del frontend
    email: str
    password: str = "prof123"
    materias: Optional[List[str]] = []

    @model_validator(mode='after')
    def resolve_nombre(self):
        if not self.nombre_completo and self.nombre:
            self.nombre_completo = self.nombre
        if not self.nombre_completo:
            self.nombre_completo = 'Sin nombre'
        return self


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


class LoginBody(BaseModel):
    email: str
    password: str


# =============================================================
# HELPERS
# =============================================================

ROL_PROFESOR = 2


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def _build_response(u: Usuario, db: Session) -> ProfesorResponse:
    prof_nombre = f"{u.primer_nombre} {u.primer_apellido}".strip()
    return ProfesorResponse(
        id_usuario=u.id_usuario,
        nombre_completo=prof_nombre,
        email=u.email,
        materias=[],
        activo=u.activo,
        total_estudiantes=0,
    )


# =============================================================
# ENDPOINTS
# =============================================================

@router.get("/", response_model=ProfesoresListResponse, summary="Listar profesores")
async def listar_profesores(db: Session = Depends(get_db)) -> ProfesoresListResponse:
    usuarios = (
        db.query(Usuario)
        .filter(Usuario.activo == True, Usuario.deleted_at == None)
        .all()
    )
    items = [_build_response(u, db) for u in usuarios]
    return ProfesoresListResponse(total=len(items), items=items)


@router.get("/{id_usuario}", response_model=ProfesorResponse, summary="Obtener profesor por ID")
async def get_profesor(id_usuario: UUID, db: Session = Depends(get_db)) -> ProfesorResponse:
    u = db.query(Usuario).filter(
        Usuario.id_usuario == id_usuario,
        Usuario.deleted_at == None,
    ).first()
    if not u:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    return _build_response(u, db)


@router.post("/", response_model=ProfesorResponse, status_code=201, summary="Crear profesor")
async def crear_profesor(body: ProfesorCreate, db: Session = Depends(get_db)) -> ProfesorResponse:
    existe = db.query(Usuario).filter(Usuario.email == body.email).first()
    if existe:
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese email")
    partes = body.nombre_completo.strip().split()
    primer_nombre = partes[0] if partes else body.nombre_completo
    primer_apellido = partes[1] if len(partes) > 1 else ""
    segundo_apellido = partes[2] if len(partes) > 2 else ""
    nuevo = Usuario(
        id_rol=ROL_PROFESOR,
        primer_nombre=primer_nombre,
        primer_apellido=primer_apellido,
        segundo_apellido=segundo_apellido,
        email=body.email,
        password_hash=_hash(body.password),
        activo=True,
        email_verificado=False,
        intentos_fallidos=0,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return _build_response(nuevo, db)


@router.put("/{id_usuario}", response_model=ProfesorResponse, summary="Actualizar profesor")
async def actualizar_profesor(
    id_usuario: UUID,
    body: ProfesorUpdate,
    db: Session = Depends(get_db),
) -> ProfesorResponse:
    u = db.query(Usuario).filter(
        Usuario.id_usuario == id_usuario,
        Usuario.deleted_at == None,
    ).first()
    if not u:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    if body.nombre_completo is not None:
        partes = body.nombre_completo.strip().split()
        u.primer_nombre = partes[0] if partes else body.nombre_completo
        u.primer_apellido = partes[1] if len(partes) > 1 else ""
        u.segundo_apellido = partes[2] if len(partes) > 2 else ""
    if body.email is not None:
        u.email = body.email
    if body.activo is not None:
        u.activo = body.activo
    db.commit()
    db.refresh(u)
    return _build_response(u, db)


@router.delete("/{id_usuario}", status_code=204, summary="Desactivar profesor")
async def desactivar_profesor(id_usuario: UUID, db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(
        Usuario.id_usuario == id_usuario,
        Usuario.deleted_at == None,
    ).first()
    if not u:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    u.activo = False
    db.commit()
    return None


@router.post("/login", summary="Login de profesor")
async def login_profesor(body: LoginBody, db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(
        Usuario.email == body.email,
        Usuario.activo == True,
        Usuario.deleted_at == None,
    ).first()
    if not u:
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    if u.password_hash != _hash(body.password):
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    nombre = f"{u.primer_nombre} {u.primer_apellido}".strip()
    return {
        "ok": True,
        "id_usuario": str(u.id_usuario),
        "nombre": nombre,
        "email": u.email,
        "rol": "admin" if u.id_rol == 1 else "profesor",
    }
