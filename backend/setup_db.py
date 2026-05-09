# setup_db.py — Schema completo 100% compatible con database/models.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from sqlalchemy import create_engine, text
from config.settings import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:

    print("=== LIMPIANDO Y RECREANDO DB ===")
    conn.execute(text("DROP SCHEMA IF EXISTS audit CASCADE"))
    conn.execute(text("DROP SCHEMA IF EXISTS processing CASCADE"))
    conn.execute(text("DROP SCHEMA IF EXISTS admin CASCADE"))
    conn.commit()

    conn.execute(text("CREATE SCHEMA admin"))
    conn.execute(text("CREATE SCHEMA processing"))
    conn.execute(text("CREATE SCHEMA audit"))
    conn.commit()
    print("OK: schemas admin, processing, audit")

    # ── ADMIN ─────────────────────────────────────────────────────
    conn.execute(text("""
        CREATE TABLE admin.roles (
            id_rol      SERIAL PRIMARY KEY,
            nombre_rol  VARCHAR(50)  NOT NULL UNIQUE,
            descripcion TEXT,
            permisos    JSONB        NOT NULL DEFAULT '[]'::jsonb,
            activo      BOOLEAN      NOT NULL DEFAULT TRUE,
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """))
    conn.commit()
    print("OK: admin.roles")

    conn.execute(text("""
        CREATE TABLE admin.usuarios (
            id_usuario        UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            id_rol            INTEGER      NOT NULL REFERENCES admin.roles(id_rol),
            primer_nombre     VARCHAR(100) NOT NULL,
            segundo_nombre    VARCHAR(100),
            primer_apellido   VARCHAR(100) NOT NULL,
            segundo_apellido  VARCHAR(100),
            email             VARCHAR(255) NOT NULL UNIQUE,
            password_hash     TEXT         NOT NULL,
            activo            BOOLEAN      NOT NULL DEFAULT TRUE,
            email_verificado  BOOLEAN      NOT NULL DEFAULT FALSE,
            ultimo_acceso     TIMESTAMPTZ,
            intentos_fallidos INTEGER      NOT NULL DEFAULT 0,
            bloqueado_hasta   TIMESTAMPTZ,
            created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            deleted_at        TIMESTAMPTZ
        )
    """))
    conn.commit()
    print("OK: admin.usuarios")

    conn.execute(text("""
        CREATE TABLE admin.estudiantes (
            id_estudiante      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            codigo_estudiante  VARCHAR(20)  UNIQUE,
            primer_nombre      VARCHAR(100) NOT NULL,
            segundo_nombre     VARCHAR(100),
            primer_apellido    VARCHAR(100) NOT NULL,
            segundo_apellido   VARCHAR(100),
            tipo_documento     VARCHAR(20),
            numero_documento   VARCHAR(30)  NOT NULL,
            fecha_nacimiento   DATE         NOT NULL,
            genero             VARCHAR(10),
            direccion          TEXT,
            telefono_contacto  VARCHAR(20),
            email              VARCHAR(255),
            nombre_acudiente   VARCHAR(200),
            telefono_acudiente VARCHAR(20),
            email_acudiente    VARCHAR(255),
            relacion_acudiente VARCHAR(50),
            grado_escolar      VARCHAR(20),
            institucion_origen VARCHAR(200),
            fecha_ingreso      DATE         NOT NULL DEFAULT CURRENT_DATE,
            fecha_retiro       DATE,
            estado             VARCHAR(20)  NOT NULL DEFAULT 'activo',
            created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            deleted_at         TIMESTAMPTZ,
            CONSTRAINT chk_estado_estudiante CHECK (estado IN ('activo','inactivo','retirado'))
        )
    """))
    conn.commit()
    print("OK: admin.estudiantes")

    # ── PROCESSING ────────────────────────────────────────────────
    conn.execute(text("""
        CREATE TABLE processing.test_templates (
            id_template      SERIAL        PRIMARY KEY,
            code             VARCHAR(10)   NOT NULL,
            subject          VARCHAR(20)   NOT NULL,
            display_name     VARCHAR(100)  NOT NULL,
            total_items      INTEGER       NOT NULL,
            time_pattern_min NUMERIC(5,2)  NOT NULL,
            answer_key       JSONB         NOT NULL DEFAULT '{}'::jsonb,
            level_rules      JSONB         NOT NULL DEFAULT '{}'::jsonb,
            activo           BOOLEAN       NOT NULL DEFAULT TRUE,
            created_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_test_code_subject UNIQUE (code, subject)
        )
    """))
    conn.commit()
    print("OK: processing.test_templates")

    conn.execute(text("""
        CREATE TABLE processing.prospectos (
            id_prospecto    UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            nombre_completo VARCHAR(200) NOT NULL,
            grado_escolar   VARCHAR(20),
            nombre_escuela  VARCHAR(200),
            fecha_prueba    DATE,
            nombre_acudiente VARCHAR(200),
            telefono        VARCHAR(20),
            created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    """))
    conn.commit()
    print("OK: processing.prospectos")

    conn.execute(text("""
        CREATE TABLE processing.processing_jobs (
            id_job             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            id_estudiante      UUID        REFERENCES admin.estudiantes(id_estudiante) ON DELETE CASCADE,
            id_prospecto       UUID        REFERENCES processing.prospectos(id_prospecto) ON DELETE SET NULL,
            id_template        INTEGER     NOT NULL REFERENCES processing.test_templates(id_template),
            source_type        VARCHAR(10) NOT NULL DEFAULT 'video',
            file_path          TEXT,
            file_name_original TEXT,
            file_size_bytes    BIGINT,
            file_hash          VARCHAR(32) NOT NULL DEFAULT '',
            status             VARCHAR(20) NOT NULL DEFAULT 'queued',
            progress_percent   INTEGER     NOT NULL DEFAULT 0,
            error_message      TEXT,
            retry_count        INTEGER     NOT NULL DEFAULT 0,
            created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            started_at         TIMESTAMPTZ,
            completed_at       TIMESTAMPTZ,
            CONSTRAINT chk_xor_sujeto CHECK (
                (id_estudiante IS NOT NULL AND id_prospecto IS NULL) OR
                (id_estudiante IS NULL AND id_prospecto IS NOT NULL)
            ),
            CONSTRAINT chk_job_status CHECK (
                status IN ('queued','processing','done','error','manual_review')
            ),
            CONSTRAINT chk_job_progress CHECK (progress_percent BETWEEN 0 AND 100),
            CONSTRAINT chk_job_completado CHECK (
                completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at
            )
        )
    """))
    conn.commit()
    print("OK: processing.processing_jobs")

    conn.execute(text("""
        CREATE TABLE processing.test_results (
            id_result       UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            id_job          UUID         NOT NULL UNIQUE REFERENCES processing.processing_jobs(id_job) ON DELETE CASCADE,
            id_prospecto    UUID         REFERENCES processing.prospectos(id_prospecto),
            id_estudiante   UUID         REFERENCES admin.estudiantes(id_estudiante),
            id_template     INTEGER      NOT NULL REFERENCES processing.test_templates(id_template),
            tipo_sujeto     VARCHAR(20)  NOT NULL,
            percentage      NUMERIC(5,2),
            semaforo        VARCHAR(10),
            study_time_min  NUMERIC(6,2),
            target_time_min NUMERIC(6,2),
            datos_resultado JSONB        NOT NULL DEFAULT '{}'::jsonb,
            created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_tipo_sujeto  CHECK (tipo_sujeto IN ('prospecto','estudiante')),
            CONSTRAINT chk_semaforo     CHECK (semaforo IS NULL OR semaforo IN ('verde','amarillo','rojo')),
            CONSTRAINT chk_percentage   CHECK (percentage IS NULL OR percentage BETWEEN 0 AND 100)
        )
    """))
    conn.commit()
    print("OK: processing.test_results")

    conn.execute(text("""
        CREATE TABLE processing.qualitative_results (
            id_qualitative     UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            id_job             UUID        NOT NULL UNIQUE REFERENCES processing.processing_jobs(id_job) ON DELETE CASCADE,
            datos_cualitativos JSONB       NOT NULL DEFAULT '{}'::jsonb,
            created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    conn.commit()
    print("OK: processing.qualitative_results")

    conn.execute(text("""
        CREATE TABLE processing.observaciones_cualitativas (
            id_observacion UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            id_result      UUID        NOT NULL UNIQUE REFERENCES processing.test_results(id_result) ON DELETE CASCADE,
            observaciones  JSONB       NOT NULL DEFAULT '{}'::jsonb,
            esta_completo  BOOLEAN     NOT NULL DEFAULT FALSE,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    conn.commit()
    print("OK: processing.observaciones_cualitativas")

    conn.execute(text("""
        CREATE TABLE processing.bulletins (
            id_bulletin          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            id_result            UUID        NOT NULL UNIQUE REFERENCES processing.test_results(id_result) ON DELETE CASCADE,
            id_template          INTEGER     NOT NULL REFERENCES processing.test_templates(id_template),
            status               VARCHAR(20) NOT NULL DEFAULT 'pending',
            datos_boletin        JSONB       NOT NULL DEFAULT '{}'::jsonb,
            puntaje_cuantitativo NUMERIC(5,2),
            puntaje_cualitativo  NUMERIC(5,2),
            puntaje_combinado    NUMERIC(5,2),
            etiqueta_combinada   VARCHAR(20),
            pdf_path             TEXT,
            pdf_size_bytes       BIGINT,
            approved_by          UUID        REFERENCES admin.usuarios(id_usuario),
            approved_at          TIMESTAMPTZ,
            delivered_at         TIMESTAMPTZ,
            generated_at         TIMESTAMPTZ,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_bulletin_status   CHECK (status IN ('pending','generating','ready','delivered','error')),
            CONSTRAINT chk_bulletin_etiqueta CHECK (
                etiqueta_combinada IS NULL OR
                etiqueta_combinada IN ('fortaleza','en_desarrollo','refuerzo','atencion')
            )
        )
    """))
    conn.commit()
    print("OK: processing.bulletins")

    # ── AUDIT ─────────────────────────────────────────────────────
    conn.execute(text("""
        CREATE TABLE audit.processing_errors (
            id_error   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            id_job     UUID        REFERENCES processing.processing_jobs(id_job),
            stage      VARCHAR(100),
            mensaje    TEXT,
            detalle    JSONB       NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    conn.commit()
    print("OK: audit.processing_errors")

    print("\n=== VERIFICACION FINAL ===")
    r = conn.execute(text("""
        SELECT table_schema||'.'||table_name
        FROM information_schema.tables
        WHERE table_schema IN ('admin','processing','audit')
        ORDER BY 1
    """))
    for row in r.fetchall():
        print(f"  ✓ {row[0]}")

print("\n✓ DB 100% LISTA Y COMPATIBLE CON ORM")