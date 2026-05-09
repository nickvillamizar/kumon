# Kumon — Sistema de Automatización de Pruebas Diagnósticas

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python) ![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-blue?logo=postgresql) ![EasyOCR](https://img.shields.io/badge/EasyOCR-ES%2FEN-orange)

API de procesamiento de pruebas diagnósticas Kumon. Sube un video de estudiante, extrae métricas cuantitativas y cualitativas mediante OCR + análisis de audio/video, calcula el semáforo de aprendizaje y genera el boletín PDF.

---

## Arquitectura

```
kumon/
├── backend/                  # FastAPI + Python
│   ├── app/
│   │   ├── main.py           # Entry point, CORS, startup
│   │   ├── routes/           # upload, jobs, results, cuestionario, dashboard
│   │   ├── schemas/          # Pydantic models
│   │   └── services/         # OCR, audio, face, PDF, processing
│   ├── config/
│   │   ├── settings.py       # Pydantic Settings (.env)
│   │   ├── database.py       # SQLAlchemy engine + session
│   │   └── cuestionarios.py  # Configuración 29 tests Kumon
│   ├── database/
│   │   ├── models.py         # ORM: admin + processing + audit schemas
│   │   └── BD_kumon_v2.sql   # Queries diagnósticas
│   └── requirements.txt
├── frontend/                 # HTML + CSS + JS vanilla
│   ├── index.html            # Panel principal
│   ├── edupanel_FINAL.html   # Dashboard admin
│   ├── css/
│   └── js/
├── .env.example              # Variables de entorno (plantilla)
├── .gitignore
└── README.md
```

---

## Stack Tecnológico

| Capa | Tecnología |
|------|------------|
| API | FastAPI 0.100+ |
| ORM | SQLAlchemy 2.0 |
| DB | PostgreSQL (Neon Cloud) |
| OCR | EasyOCR (es + en) |
| PDF | WeasyPrint / ReportLab |
| Audio | librosa / scipy |
| Video | OpenCV |
| Config | Pydantic Settings v2 |
| Frontend | HTML5 + CSS3 + JS Vanilla |

---

## Instalación y Setup

### 1. Clonar el repo
```bash
git clone https://github.com/nickvillamizar/kumon.git
cd kumon/backend
```

### 2. Crear entorno virtual e instalar dependencias
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 3. Configurar variables de entorno
```bash
cp ../.env.example .env
# Edita .env con tus credenciales de PostgreSQL
```

### 4. Crear la base de datos
```bash
python setup_db.py
```

### 5. Iniciar el servidor
```bash
python -m uvicorn app.main:app --reload --port 8000
```

Abre **http://127.0.0.1:8000/docs** para la documentación interactiva Swagger.

---

## Endpoints Principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/v1/upload/video` | Sube video y crea job de procesamiento |
| `GET` | `/api/v1/jobs/{job_id}` | Consulta estado del job |
| `GET` | `/api/v1/results/{result_id}` | Obtiene resultados OCR |
| `GET` | `/api/v1/cuestionario/{result_id}` | Formulario cualitativo |
| `GET` | `/api/v1/dashboard/stats` | KPIs generales |
| `GET` | `/api/v1/dashboard/health` | Health check DB |

---

## Esquema de Base de Datos

```
Schema admin:
  roles → usuarios → estudiantes

Schema processing:
  test_templates → prospectos
  processing_jobs → test_results → bulletins
                 ↘ qualitative_results
                   test_results → observaciones_cualitativas

Schema audit:
  processing_errors
```

---

## Variables de Entorno

Ver `.env.example` para la lista completa. Las principales:

```env
DATABASE_URL=postgresql://user:pass@host:5432/kumon_db
SECRET_KEY=clave-secreta-aleatoria
ENVIRONMENT=development
ALLOWED_VIDEO_EXTENSIONS=["mp4","avi","mov","mkv"]
VALID_SUBJECTS=["matematicas","lenguaje","ingles"]
```

---

## Desarrolladores

- **Nicolás Ramírez Villamizar** — Backend & Architecture
- **Camilo Alexander Rubio Pazmiño** — Services & Integration

---

## Licencia

Proyecto académico — Universidad. Todos los derechos reservados.
