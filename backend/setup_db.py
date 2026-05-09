# setup_db.py v3 - Inspecciona y crea todo limpio
import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from sqlalchemy import create_engine, text
from config.settings import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:

    # ── PASO 0: Ver qué existe ya en Neon ────────────────
    print("=== INSPECCIONANDO DB ACTUAL ===")
    result = conn.execute(text("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema IN ('admin','processing','audit')
        ORDER BY table_schema, table_name
    """))
    rows = result.fetchall()
    if rows:
        for r in rows:
            print(f"  EXISTE: {r[0]}.{r[1]}")
    else:
        print("  (sin tablas aun)")

    # ── PASO 1: DROP TODO y empezar limpio ────────────────
    print("\n=== LIMPIANDO SCHEMAS ===")
    conn.execute(text("DROP SCHEMA IF EXISTS audit CASCADE"))
    conn.execute(text("DROP SCHEMA IF EXISTS processing CASCADE"))
    conn.execute(text("DROP SCHEMA IF EXISTS admin CASCADE"))
    conn.commit()
    print("   OK: schemas eliminados")

    # ── PASO 2: Recrear schemas ───────────────────────────
    conn.execute(text("CREATE SCHEMA admin"))
    conn.execute(text("CREATE SCHEMA processing"))
    conn.execute(text("CREATE SCHEMA audit"))
    conn.commit()
    print("   OK: schemas creados")

    # ── PASO 3: admin (sin deps) ──────────────────────────
    print("\n=== CREANDO TABLAS admin ===")
    conn.execute(text("""
        CREATE TABLE admin.roles (
            id_rol      SERIAL PRIMARY KEY,
            nombre_rol  VARCHAR(50) NOT NULL UNIQUE,
            descripcion TEXT,
            created_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL
        )
    """))
    conn.commit()
    print("   OK: admin.roles")

    conn.execute(text("""
        CREATE TABLE admin.usuarios (
            id_usuario    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            id_rol        INTEGER NOT NULL REFERENCES admin.roles(id_rol),
            nombre        VARCHAR(255) NOT NULL,
            email         VARCHAR(255) NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            activo        BOOLEAN DEFAULT TRUE NOT NULL,
            created_at    TIMESTAMPTZ DEFAULT NOW() NOT NULL,
            updated_at    TIMESTAMPTZ DEFAULT NOW() NOT NULL
        )
    """))
    conn.commit()
    print("   OK: admin.usuarios")

    # Verificar que id_usuario existe
    r = conn.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema='admin' AND table_name='usuarios'
        ORDER BY ordinal_position
    """))
    cols = [row[0] for row in r.fetchall()]
    print(f"   admin.usuarios columnas: {cols}")

    conn.execute(text("""
        CREATE TABLE admin.estudiantes (
            id_estudiante UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            nombre        VARCHAR(255) NOT NULL,
            apellido      VARCHAR(255),
            materia       VARCHAR(100),
            nivel         VARCHAR(50),
            orientador    VARCHAR(255),
            activo        BOOLEAN DEFAULT TRUE NOT NULL,
            created_at    TIMESTAMPTZ DEFAULT NOW() NOT NULL,
            updated_at    TIMESTAMPTZ DEFAULT NOW() NOT NULL
        )
    """))
    conn.commit()
    print("   OK: admin.estudiantes")

    # ── PASO 4: processing ────────────────────────────────
    print("\n=== CREANDO TABLAS processing ===")
    conn.execute(text("""
        CREATE TABLE processing.test_templates (
            id_template   SERIAL PRIMARY KEY,
            nombre        VARCHAR(255) NOT NULL,
            materia       VARCHAR(100),
            nivel         VARCHAR(50),
            descripcion   TEXT,
            metadata_     JSONB DEFAULT '{}'::jsonb,
            activo        BOOLEAN DEFAULT TRUE NOT NULL,
            created_at    TIMESTAMPTZ DEFAULT NOW() NOT NULL
        )
    """))
    conn.commit()
    print("   OK: processing.test_templates")

    conn.execute(text("""
        CREATE TABLE processing.prospectos (
            id_prospecto  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            nombre        VARCHAR(255) NOT NULL,
            apellido      VARCHAR(255),
            email         VARCHAR(255),
            telefono      VARCHAR(50),
            created_at    TIMESTAMPTZ DEFAULT NOW() NOT NULL
        )
    """))
    conn.commit()
    print("   OK: processing.prospectos")

    conn.execute(text("""
        CREATE TABLE processing.processing_jobs (
            id_job        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            id_estudiante UUID REFERENCES admin.estudiantes(id_estudiante) ON DELETE CASCADE,
            id_prospecto  UUID REFERENCES processing.prospectos(id_prospecto) ON DELETE SET NULL,
            id_template   INTEGER REFERENCES processing.test_templates(id_template),
            video_path    TEXT,
            status        VARCHAR(20) DEFAULT 'pending' NOT NULL,
            error_message TEXT,
            created_at    TIMESTAMPTZ DEFAULT NOW() NOT NULL,
            updated_at    TIMESTAMPTZ DEFAULT NOW() NOT NULL,
            CONSTRAINT chk_xor_sujeto CHECK (
                (id_estudiante IS NOT NULL AND id_prospecto IS NULL) OR
                (id_estudiante IS NULL AND id_prospecto IS NOT NULL)
            ),
            CONSTRAINT chk_job_status CHECK (
                status IN ('pending','processing','completed','error')
            )
        )
    """))
    conn.commit()
    print("   OK: processing.processing_jobs")

    conn.execute(text("""
        CREATE TABLE processing.test_results (
            id_result       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            id_job          UUID NOT NULL UNIQUE REFERENCES processing.processing_jobs(id_job) ON DELETE CASCADE,
            id_prospecto    UUID REFERENCES processing.prospectos(id_prospecto),
            id_estudiante   UUID REFERENCES admin.estudiantes(id_estudiante),
            id_template     INTEGER REFERENCES processing.test_templates(id_template),
            tipo_sujeto     VARCHAR(20) NOT NULL,
            puntaje_total   NUMERIC(5,2),
            semaforo        VARCHAR(10),
            datos_resultado JSONB DEFAULT '{}'::jsonb,
            created_at      TIMESTAMPTZ DEFAULT NOW() NOT NULL,
            CONSTRAINT chk_tipo_sujeto CHECK (tipo_sujeto IN ('prospecto','estudiante')),
            CONSTRAINT chk_semaforo CHECK (semaforo IS NULL OR semaforo IN ('verde','amarillo','rojo'))
        )
    """))
    conn.commit()
    print("   OK: processing.test_results")

    conn.execute(text("""
        CREATE TABLE processing.qualitative_results (
            id_qualitative     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            id_job             UUID NOT NULL UNIQUE REFERENCES processing.processing_jobs(id_job) ON DELETE CASCADE,
            datos_cualitativos JSONB DEFAULT '{}'::jsonb,
            created_at         TIMESTAMPTZ DEFAULT NOW() NOT NULL
        )
    """))
    conn.commit()
    print("   OK: processing.qualitative_results")

    conn.execute(text("""
        CREATE TABLE processing.observaciones_cualitativas (
            id_observacion UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            id_result      UUID NOT NULL UNIQUE REFERENCES processing.test_results(id_result) ON DELETE CASCADE,
            observaciones  JSONB DEFAULT '{}'::jsonb,
            esta_completo  BOOLEAN DEFAULT FALSE NOT NULL,
            created_at     TIMESTAMPTZ DEFAULT NOW() NOT NULL,
            updated_at     TIMESTAMPTZ DEFAULT NOW() NOT NULL
        )
    """))
    conn.commit()
    print("   OK: processing.observaciones_cualitativas")

    conn.execute(text("""
        CREATE TABLE processing.bulletins (
            id_bulletin          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            id_result            UUID NOT NULL UNIQUE REFERENCES processing.test_results(id_result) ON DELETE CASCADE,
            id_template          INTEGER NOT NULL REFERENCES processing.test_templates(id_template),
            status               VARCHAR(20) DEFAULT 'pending' NOT NULL,
            datos_boletin        JSONB DEFAULT '{}'::jsonb NOT NULL,
            puntaje_cuantitativo NUMERIC(5,2),
            puntaje_cualitativo  NUMERIC(5,2),
            puntaje_combinado    NUMERIC(5,2),
            etiqueta_combinada   VARCHAR(20),
            pdf_path             TEXT,
            pdf_size_bytes       BIGINT,
            approved_by          UUID REFERENCES admin.usuarios(id_usuario),
            approved_at          TIMESTAMPTZ,
            delivered_at         TIMESTAMPTZ,
            generated_at         TIMESTAMPTZ,
            created_at           TIMESTAMPTZ DEFAULT NOW() NOT NULL,
            CONSTRAINT chk_bulletin_status CHECK (
                status IN ('pending','generating','ready','delivered','error')
            ),
            CONSTRAINT chk_bulletin_etiqueta CHECK (
                etiqueta_combinada IS NULL OR
                etiqueta_combinada IN ('fortaleza','en_desarrollo','refuerzo','atencion')
            )
        )
    """))
    conn.commit()
    print("   OK: processing.bulletins")

    # ── PASO 5: audit ─────────────────────────────────────
    print("\n=== CREANDO TABLAS audit ===")
    conn.execute(text("""
        CREATE TABLE audit.processing_errors (
            id_error   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            id_job     UUID REFERENCES processing.processing_jobs(id_job),
            stage      VARCHAR(100),
            mensaje    TEXT,
            detalle    JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
        )
    """))
    conn.commit()
    print("   OK: audit.processing_errors")

    # ── VERIFICACION FINAL ────────────────────────────────
    print("\n=== VERIFICACION FINAL ===")
    result = conn.execute(text("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema IN ('admin','processing','audit')
        ORDER BY table_schema, table_name
    """))
    for r in result.fetchall():
        print(f"   ✓ {r[0]}.{r[1]}")

print("\n✓ BASE DE DATOS 100% LISTA")