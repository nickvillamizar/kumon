from __future__ import annotations
import uuid
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Column, Date, DateTime,
    ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship
from config.database import Base

TIMESTAMPTZ = DateTime(timezone=True)


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = {"schema": "admin"}
    id_rol = Column(Integer, primary_key=True, autoincrement=True)
    nombre_rol = Column(String(50), nullable=False, unique=True)
    descripcion = Column(Text)
    permisos = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    activo = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(TIMESTAMPTZ, nullable=False, server_default=text("NOW()"))
    updated_at = Column(TIMESTAMPTZ, nullable=False, server_default=text("NOW()"))
    usuarios = relationship("Usuario", back_populates="rol", lazy="select")


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = {"schema": "admin"}
    id_usuario = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_rol = Column(Integer, ForeignKey("admin.roles.id_rol"), nullable=False)
    primer_nombre = Column(String(100), nullable=False)
    segundo_nombre = Column(String(100))
    primer_apellido = Column(String(100), nullable=False)
    segundo_apellido = Column(String(100))
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    activo = Column(Boolean, nullable=False, server_default=text("true"))
    email_verificado = Column(Boolean, nullable=False, server_default=text("false"))
    ultimo_acceso = Column(TIMESTAMPTZ)
    intentos_fallidos = Column(Integer, nullable=False, server_default=text("0"))
    bloqueado_hasta = Column(TIMESTAMPTZ)
    created_at = Column(TIMESTAMPTZ, nullable=False, server_default=text("NOW()"))
    updated_at = Column(TIMESTAMPTZ, nullable=False, server_default=text("NOW()"))
    deleted_at = Column(TIMESTAMPTZ)
    rol = relationship("Role", back_populates="usuarios")

    @property
    def nombre_completo(self) -> str:
        partes = [self.primer_nombre, self.segundo_nombre, self.primer_apellido, self.segundo_apellido]
        return " ".join(p for p in partes if p)

    @property
    def is_active(self) -> bool:
        return self.activo and self.deleted_at is None


class Student(Base):
    __tablename__ = "estudiantes"
    __table_args__ = {"schema": "admin"}
    id_estudiante = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo_estudiante = Column(String(20), unique=True)
    primer_nombre = Column(String(100), nullable=False)
    segundo_nombre = Column(String(100))
    primer_apellido = Column(String(100), nullable=False)
    segundo_apellido = Column(String(100))
    tipo_documento = Column(String(10), nullable=False, server_default=text("'TI'"))
    numero_documento = Column(String(30), nullable=False)
    fecha_nacimiento = Column(Date, nullable=False)
    genero = Column(String(20))
    direccion = Column(Text)
    telefono_contacto = Column(String(20))
    email = Column(String(255))
    nombre_acudiente = Column(String(200))
    telefono_acudiente = Column(String(20))
    email_acudiente = Column(String(255))
    relacion_acudiente = Column(String(50))
    grado_escolar = Column(String(50))
    institucion_origen = Column(String(200))
    fecha_ingreso = Column(Date, nullable=False, server_default=text("CURRENT_DATE"))
    fecha_retiro = Column(Date)
    estado = Column(String(20), nullable=False, server_default=text("'activo'"))
    created_at = Column(TIMESTAMPTZ, nullable=False, server_default=text("NOW()"))
    updated_at = Column(TIMESTAMPTZ, nullable=False, server_default=text("NOW()"))
    deleted_at = Column(TIMESTAMPTZ)
    processing_jobs = relationship("ProcessingJob", back_populates="estudiante", foreign_keys="[ProcessingJob.id_estudiante]", lazy="select")
    test_results = relationship("TestResult", back_populates="estudiante", foreign_keys="[TestResult.id_estudiante]", lazy="select")

    @property
    def nombre_completo(self) -> str:
        partes = [self.primer_nombre, self.segundo_nombre, self.primer_apellido, self.segundo_apellido]
        return " ".join(p for p in partes if p)

    @property
    def is_active(self) -> bool:
        return self.estado == "activo" and self.deleted_at is None


class TestTemplate(Base):
    __tablename__ = "test_templates"
    __table_args__ = (
        UniqueConstraint("code", "subject", name="uq_test_code_subject"),
        {"schema": "processing"},
    )
    id_template = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), nullable=False)
    subject = Column(String(20), nullable=False)
    display_name = Column(String(100), nullable=False)
    grade_level = Column(String(50))
    total_items = Column(Integer, nullable=False)
    time_pattern_min = Column(Numeric(5, 2), nullable=False)
    description = Column(Text)
    answer_key = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    level_rules = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    extraction_rules = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    metadata_ = Column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(TIMESTAMPTZ, nullable=False, server_default=text("NOW()"))
    updated_at = Column(TIMESTAMPTZ, nullable=False, server_default=text("NOW()"))
    processing_jobs = relationship("ProcessingJob", back_populates="template", lazy="select")
    test_results = relationship("TestResult", back_populates="template", lazy="select")
    bulletins = relationship("Bulletin", back_populates="template", lazy="select")


class Prospecto(Base):
    __tablename__ = "prospectos"
    __table_args__ = {"schema": "processing"}
    id_prospecto = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre_completo = Column(Text, nullable=False)
    grado_escolar = Column(Text)
    nombre_escuela = Column(Text)
    fecha_prueba = Column(Date)
    nombre_acudiente = Column(Text)
    telefono = Column(Text)
    created_at = Column(TIMESTAMPTZ, nullable=False, server_default=text("NOW()"))
    processing_jobs = relationship("ProcessingJob", back_populates="prospecto", foreign_keys="[ProcessingJob.id_prospecto]", lazy="select")
    test_results = relationship("TestResult", back_populates="prospecto", foreign_keys="[TestResult.id_prospecto]", lazy="select")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    __table_args__ = (
        CheckConstraint(
            "(id_estudiante IS NOT NULL AND id_prospecto IS NULL) OR "
            "(id_estudiante IS NULL AND id_prospecto IS NOT NULL)",
            name="chk_xor_sujeto",
        ),
        CheckConstraint(
            "status IN ('queued','processing','done','error','manual_review')",
            name="chk_job_status",
        ),
        CheckConstraint(
            "progress_percent BETWEEN 0 AND 100",
            name="chk_job_progress",
        ),
        {"schema": "processing"},
    )
    id_job = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_estudiante = Column(UUID(as_uuid=True), ForeignKey("admin.estudiantes.id_estudiante", ondelete="CASCADE"), nullable=True)
    id_prospecto = Column(UUID(as_uuid=True), ForeignKey("processing.prospectos.id_prospecto", ondelete="SET NULL"), nullable=True)
    id_template = Column(Integer, ForeignKey("processing.test_templates.id_template"), nullable=False)
    file_path = Column(Text)
    file_name_original = Column(Text)
    file_size_bytes = Column(BigInteger)
    file_hash = Column(String(32))
    status = Column(String(20), nullable=False, server_default=text("'queued'"))
    progress_percent = Column(Integer, nullable=False, server_default=text("0"))
    error_message = Column(Text)
    retry_count = Column(Integer, nullable=False, server_default=text("0"))
    created_at = Column(TIMESTAMPTZ, nullable=False, server_default=text("NOW()"))
    estudiante = relationship("Student", back_populates="processing_jobs", foreign_keys=[id_estudiante], lazy="select")
    prospecto = relationship("Prospecto", back_populates="processing_jobs", foreign_keys=[id_prospecto], lazy="select")
    template = relationship("TestTemplate", back_populates="processing_jobs", lazy="select")
    test_result = relationship("TestResult", back_populates="job", uselist=False, lazy="select")
    qualitative_result = relationship("QualitativeResult", back_populates="job", uselist=False, lazy="select")
    processing_errors = relationship("ProcessingError", back_populates="job", lazy="select")

    @property
    def is_prospecto(self) -> bool:
        return self.id_prospecto is not None

    @property
    def is_estudiante(self) -> bool:
        return self.id_estudiante is not None

    @property
    def is_done(self) -> bool:
        return self.status == "done"

    @property
    def is_error(self) -> bool:
        return self.status == "error"

    @property
    def needs_review(self) -> bool:
        return self.status == "manual_review"

    @property
    def sujeto_nombre(self) -> str:
        if self.prospecto:
            return self.prospecto.nombre_completo
        if self.estudiante:
            return self.estudiante.nombre_completo
        return "Desconocido"


class TestResult(Base):
    __tablename__ = "test_results"
    __table_args__ = (
        CheckConstraint("semaforo IS NULL OR semaforo IN ('verde','amarillo','rojo')", name="chk_result_semaforo"),
        CheckConstraint("tipo_sujeto IN ('prospecto','estudiante')", name="chk_result_tipo_sujeto"),
        CheckConstraint("percentage IS NULL OR percentage BETWEEN 0 AND 100", name="chk_result_percentage"),
        {"schema": "processing"},
    )
    id_result = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_job = Column(UUID(as_uuid=True), ForeignKey("processing.processing_jobs.id_job", ondelete="CASCADE"), nullable=False, unique=True)
    id_prospecto = Column(UUID(as_uuid=True), ForeignKey("processing.prospectos.id_prospecto"), nullable=True)
    id_estudiante = Column(UUID(as_uuid=True), ForeignKey("admin.estudiantes.id_estudiante"), nullable=True)
    id_template = Column(Integer, ForeignKey("processing.test_templates.id_template"), nullable=False)
    tipo_sujeto = Column(String(20), nullable=False)
    test_date = Column(Date)
    ws = Column(String(20))
    study_time_min = Column(Numeric(6, 2))
    target_time_min = Column(Numeric(6, 2))
    correct_answers = Column(Integer)
    total_questions = Column(Integer)
    percentage = Column(Numeric(5, 2))
    current_level = Column(String(30))
    starting_point = Column(String(50))
    semaforo = Column(String(10))
    recommendation = Column(Text)
    confidence_score = Column(Numeric(4, 3))
    needs_manual_review = Column(Boolean, nullable=False, server_default=text("false"))
    raw_ocr_data = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    sections_detail = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(TIMESTAMPTZ, nullable=False, server_default=text("NOW()"))
    job = relationship("ProcessingJob", back_populates="test_result", lazy="select")
    prospecto = relationship("Prospecto", back_populates="test_results", foreign_keys=[id_prospecto], lazy="select")
    estudiante = relationship("Student", back_populates="test_results", foreign_keys=[id_estudiante], lazy="select")
    template = relationship("TestTemplate", back_populates="test_results", lazy="select")
    observacion_cualitativa = relationship("ObservacionCualitativa", back_populates="result", uselist=False, cascade="all, delete-orphan", lazy="select")
    bulletin = relationship("Bulletin", back_populates="result", uselist=False, cascade="all, delete-orphan", lazy="select")


class QualitativeResult(Base):
    __tablename__ = "qualitative_results"
    __table_args__ = {"schema": "processing"}
    id_qualitative = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_job = Column(UUID(as_uuid=True), ForeignKey("processing.processing_jobs.id_job", ondelete="CASCADE"), nullable=False, unique=True)
    time_per_section = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    num_rewrites = Column(Integer, nullable=False, server_default=text("0"))
    pause_events = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    activity_ratio = Column(Numeric(4, 3))
    stroke_detail = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    vad_segments = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    speech_rate = Column(Numeric(5, 2))
    silence_events = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    gaze_data = Column(JSONB, nullable=True)
    prefills = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    auto_captured_flags = Column(ARRAY(Text), nullable=False, server_default=text("'{}'::text[]"))
    processing_ms = Column(Integer)
    created_at = Column(TIMESTAMPTZ, nullable=False, server_default=text("NOW()"))
    job = relationship("ProcessingJob", back_populates="qualitative_result", lazy="select")


class ObservacionCualitativa(Base):
    __tablename__ = "observaciones_cualitativas"
    __table_args__ = (
        CheckConstraint(
            "etiqueta_cualitativa IS NULL OR etiqueta_cualitativa IN ('fortaleza','en_desarrollo','refuerzo','atencion')",
            name="chk_obs_etiqueta_cualitativa",
        ),
        {"schema": "processing"},
    )
    id_observacion = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_result = Column(UUID(as_uuid=True), ForeignKey("processing.test_results.id_result", ondelete="CASCADE"), nullable=False, unique=True)
    subject = Column(String(20), nullable=False)
    test_code = Column(String(10), nullable=False)
    respuestas = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    completado_por = Column(Text)
    completado_at = Column(TIMESTAMPTZ)
    created_at = Column(TIMESTAMPTZ, nullable=False, server_default=text("NOW()"))
    puntaje_cualitativo = Column(Numeric(5, 2))
    etiqueta_cualitativa = Column(String(30))
    detalle_secciones = Column(JSONB)
    observacion_libre = Column(Text)
    correcciones_orientador = Column(JSONB, server_default=text("'{}'::jsonb"))
    esta_completo = Column(Boolean, nullable=False, server_default=text("false"))
    result = relationship("TestResult", back_populates="observacion_cualitativa", lazy="select")


class Bulletin(Base):
    __tablename__ = "bulletins"
    __table_args__ = (
        CheckConstraint("status IN ('pending','generating','ready','delivered','error')", name="chk_bulletin_status"),
        CheckConstraint("etiqueta_combinada IS NULL OR etiqueta_combinada IN ('fortaleza','en_desarrollo','refuerzo','atencion')", name="chk_bulletin_etiqueta"),
        {"schema": "processing"},
    )
    id_bulletin = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_result = Column(UUID(as_uuid=True), ForeignKey("processing.test_results.id_result", ondelete="CASCADE"), nullable=False, unique=True)
    id_template = Column(Integer, ForeignKey("processing.test_templates.id_template"), nullable=False)
    status = Column(String(20), nullable=False, server_default=text("'pending'"))
    datos_boletin = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    puntaje_cuantitativo = Column(Numeric(5, 2))
    puntaje_cualitativo = Column(Numeric(5, 2))
    puntaje_combinado = Column(Numeric(5, 2))
    etiqueta_combinada = Column(String(20))
    pdf_path = Column(Text)
    pdf_size_bytes = Column(BigInteger)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("admin.usuarios.id_usuario"))
    approved_at = Column(TIMESTAMPTZ)
    delivered_at = Column(TIMESTAMPTZ)
    generated_at = Column(TIMESTAMPTZ)
    created_at = Column(TIMESTAMPTZ, nullable=False, server_default=text("NOW()"))
    result = relationship("TestResult", back_populates="bulletin", lazy="select")
    template = relationship("TestTemplate", back_populates="bulletins", lazy="select")


class ProcessingError(Base):
    __tablename__ = "processing_errors"
    __table_args__ = {"schema": "audit"}
    id_error = Column(BigInteger, primary_key=True, autoincrement=True)
    id_job = Column(UUID(as_uuid=True), ForeignKey("processing.processing_jobs.id_job"), nullable=True)
    stage = Column(String(50), nullable=False)
    error_type = Column(String(100))
    error_detail = Column(Text)
    stack_trace = Column(Text)
    created_at = Column(TIMESTAMPTZ, nullable=False, server_default=text("NOW()"))
    job = relationship("ProcessingJob", back_populates="processing_errors", lazy="select")
