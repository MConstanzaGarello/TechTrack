# TechTrack

Sistema de Gestión y Trazabilidad de Recursos Tecnológicos del área de IT.
Proyecto de Seminario Integrador, Ingeniería en Sistemas de Información, UTN FRSFCO, 2026.

Autora: María Constanza Garello.

## Alcance de esta versión (iteración 1)

| Funcionalidad | Historias (Entregable 2) |
|---|---|
| Registrar un movimiento de un modelo entre ubicaciones, con validación en el servidor | HU-07 |
| Rechazar movimientos que superan la cantidad registrada en el origen | HU-08 |
| Consultar la disponibilidad por modelo y ubicación (versión básica, con filtros por modelo/tipo y ubicación) | HU-12 |
| Consultar el historial de operaciones, general o por modelo (versión básica, solo lectura) | HU-14 |
| Inicio de sesión y roles: **Analista de Soporte IT** (registra y consulta) y **BP del área de IT** (solo consulta) | T-02 · RNF-14, RNF-15 |

**Fuera de esta versión:** importación de Máster e Inventario, asignaciones,
altas, bajas, equipos con número de serie, filtros del historial, audio por
WhatsApp e insumos. La página de inicio los muestra como "Planificado", sin
botones que aparenten funcionar.

### Reglas de negocio implementadas

- Las cantidades **no se guardan ni se editan**: se calculan sumando las
  operaciones registradas (RNF-11).
- Cada movimiento se valida en el servidor:
  - cantidad entera mayor que cero;
  - origen distinto del destino;
  - modelo y ubicaciones activos;
  - cantidad suficiente en el origen (HU-08).
- Cada movimiento se registra dentro de una transacción que bloquea el modelo,
  para que dos analistas que operan a la vez no dejen cantidades negativas (RNF-08).
- El historial es de **solo lectura**: las operaciones no se pueden editar ni
  borrar, ni desde la aplicación ni desde el panel de administración. Un error
  se corrige registrando un **movimiento inverso** (RNF-16).
- El rol BP no puede registrar movimientos, ni desde el menú ni por URL directa
  (devuelve 403).

### Datos iniciales

El comando `cargar_demo` carga el catálogo de equipamiento con su nombre
estándar (92 modelos), las ubicaciones (warehouses, sectores en uso y plantas)
y las cantidades de partida de la planilla Inventario, definidos en
`inventario/datos_iniciales.py`. También crea los usuarios de prueba
`analista.demo` y `bp.demo`, con la contraseña que se indique al ejecutarlo.
No duplica datos si se ejecuta más de una vez.

## Requisitos

- Python **3.11**
- Git

## Instalación local (Windows, PowerShell)

```powershell
cd C:\TechTrack
py -3.11 -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py cargar_demo --password "<tu-contraseña-demo>"
python manage.py runserver
```

Abrir http://127.0.0.1:8000 e ingresar con `analista.demo` o `bp.demo`.

Para usar el panel de administración (http://127.0.0.1:8000/admin/) y cargar
modelos o ubicaciones:

```powershell
python manage.py createsuperuser
```

## Pruebas automatizadas

```powershell
python manage.py test
```

Con SQLite se ejecutan todas las pruebas menos la de concurrencia, que se
omite porque requiere PostgreSQL. Para ejecutarla, definir `DATABASE_URL` con
una base PostgreSQL de prueba.

## Variables de entorno

| Variable | Uso | En la PC | En Render |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | Clave secreta de Django | Opcional (hay una clave solo para desarrollo) | **Obligatoria** |
| `DJANGO_DEBUG` | Modo depuración | `True` por defecto | `False` por defecto |
| `DATABASE_URL` | Base de datos | Sin definir: usa SQLite | **Obligatoria**: PostgreSQL |
| `DJANGO_ALLOWED_HOSTS` | Hosts adicionales, separados por coma | Opcional | Opcional (el host de Render se agrega solo) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Orígenes adicionales | Opcional | Opcional |
| `TECHTRACK_DEMO_PASSWORD` | Contraseña de los usuarios demo | Opcional | Opcional |

Render define automáticamente `RENDER` y `RENDER_EXTERNAL_HOSTNAME`. Cuando existe
`RENDER`, la aplicación activa la configuración de producción: HTTPS, cookies
seguras y archivos estáticos comprimidos. Además, se niega a arrancar sin
`DATABASE_URL`, para no usar SQLite en producción.

## Despliegue en Render

> No crear servicios pagos sin decidirlo antes. Ver la sección "Costos".

El archivo `render.yaml` (Blueprint) define todo el despliegue con planes
gratuitos: una base **PostgreSQL** (`techtrack-db`) y un **Web Service**
(`techtrack`) conectado a ella.

1. Subir el repositorio a GitHub.
2. En Render: **New → Blueprint**, elegir el repositorio `TechTrack` y confirmar.
3. Render pide el valor de `TECHTRACK_DEMO_PASSWORD`: la contraseña de los
   usuarios de prueba (mínimo 8 caracteres, no solo números).
   `DJANGO_SECRET_KEY` se genera sola y `DATABASE_URL` se conecta sola.
4. En cada despliegue se ejecuta: instalación de dependencias, `collectstatic`,
   `migrate` y `cargar_demo` (que no duplica datos).
5. Abrir la URL `https://techtrack-xxxx.onrender.com` e ingresar con
   `analista.demo` o `bp.demo`.

**Actualizar:** cada `git push` a `main` vuelve a desplegar.
**Volver atrás:** en Render, *Events* → elegir un despliegue anterior → *Rollback*.

La versión de Python también queda fijada en `.python-version`.

## Costos

Render ofrece planes gratuitos con limitaciones:

- el servicio web se "duerme" cuando nadie lo usa;
- la base PostgreSQL gratuita vence después de un período.

Antes de elegir un plan, consultar las condiciones vigentes en
https://render.com/pricing. Esta versión no requiere ningún servicio pago.

## Estructura

```
techtrack/            configuración del proyecto (settings, urls, wsgi)
inventario/
  models.py           Ubicacion, ModeloRecurso, Operacion (inmutable)
  services.py         servicio de operaciones: movimientos y cálculo de cantidades
  datos_iniciales.py  catálogo, ubicaciones y cantidades de partida
  roles.py            grupos Analista de Soporte IT y BP del área de IT
  forms.py · views.py · urls.py · admin.py
  management/commands/cargar_demo.py
  tests/              pruebas de reglas, vistas y concurrencia
templates/            base, inicio de sesión, 403 y 404
static/               estilos y Bootstrap 5.3.3 (incluido en el repositorio)
docs/                 propuesta de cambio de secuencia del roadmap
render.yaml           despliegue en Render (Blueprint)
.env.example          nombres de las variables de entorno, sin valores
```
