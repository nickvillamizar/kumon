"""
database/models_horario.py
Modelo ORM para la tabla admin.clases_horario.
Se importa desde horarios.py sin tocar el models.py principal.
"""
from __future__ import annotations
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import text
from config.database import Base


class ClaseHorario(Base):
    """Horarios de clase asignados a estudiantes - tabla admin.clases_horario."""
    __tablename__ = "clases_horario"
    __table_args__ = {"schema": "admin"}

    id_horario    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_estudiante = Column(UUID(as_uuid=True), ForeignKey("admin.estudiantes.id_estudiante"), nullable=False)
    id_profesor   = Column(UUID(as_uuid=True), ForeignKey("admin.usuarios.id_usuario"), nullable=True)
    dia           = Column(String(20), nullable=False)
    hora_inicio   = Column(String(10), nullable=False)
    hora_fin      = Column(String(10), nullable=False)
    materia       = Column(String(50))
    activo        = Column(Boolean, nullable=False, server_default=text("true"))
    created_at    = Column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    def __repr__(self) -> str:
        return f"<ClaseHorario {self.id_horario} {self.dia} {self.hora_inicio}>"
