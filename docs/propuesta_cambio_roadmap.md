# Propuesta de cambio de secuencia del roadmap (Entregable 3)

**Estado:** propuesta para revisión. El Entregable 3 v3 **no fue modificado**.
**Fecha:** 19/10/2026

## Motivo

El Entregable 3 ubica la importación de Máster e Inventario (HU-16, HU-17) en el
Sprint 1, porque el sistema real necesita partir de esos datos. Para la iteración 1
se decidió no usar archivos reales de la organización. Una importación probada
solo con archivos inventados demuestra poco del problema validado.

Se propone adelantar el núcleo del problema, el registro de movimientos con
historial, y pasar la importación al Sprint 2. **No cambia el alcance:** son las
mismas 9 historias comprometidas al 16/11 y el MVP sigue siendo de 14 historias.

## Qué cambia exactamente en el Entregable 3

| Lugar del Entregable 3 v3 | Dice hoy | Propuesta |
|---|---|---|
| Tabla 7 (backlog), columna Planificación | HU-16 y HU-17: Sprint 1 · HU-07, HU-08 y HU-14: Sprint 2 · HU-12: Sprint 3 | HU-07, HU-08 y HU-14 (básica): Sprint 1 · HU-12: Sprint 1 (básica) y Sprint 3 (completa) · HU-16 y HU-17: Sprint 2 |
| Tabla 8 (tareas técnicas) | T-01 a T-04 | Agregar **T-05: comando de carga de datos ficticios de demostración** (Sprint 1), claramente identificado como propuesta de planificación y no como historia de usuario |
| Tabla 9 (roadmap), Sprint 1 | T-02, T-03, HU-16, HU-17 | T-02, T-03, T-05, HU-07, HU-08, HU-14 (básica), HU-12 (básica) |
| Tabla 9 (roadmap), Sprint 2 | HU-07, HU-08, HU-03, HU-14 | HU-16, HU-17, HU-03 |
| Tabla 9 (roadmap), Sprint 3 | HU-12, HU-10, HU-11, T-04 | HU-12 (completa), HU-10, HU-11, T-04 (sin cambios de contenido) |
| Sección 7, párrafo "Dentro del MVP, el orden responde a dependencias: primero los datos (importación)…" | Importación primero | Primero el servicio de operaciones (movimientos e historial) con datos ficticios, luego la importación, que carga los datos reales como operaciones de ese mismo servicio |
| Sección 8, párrafo de dependencias | "no se pueden construir operaciones sin el modelo de datos y la importación" | Las operaciones dependen del modelo de datos (T-02); la importación depende del servicio de operaciones, porque registra las cantidades iniciales como operaciones |
| Tabla 12, R-01 | Sin cambio de contenido | Aclarar que el sistema **no se usa con datos reales** hasta completar HU-17 |
| Tabla 13, R-06 | "pruebas con copias de los archivos reales en el Sprint 1" | Pasa al Sprint 2 |
| Tabla 10 (estado al 16/11) | 9 historias implementadas | Sin cambios |

## Nueva secuencia propuesta

| Sprint | Fechas (propuestas) | Contenido |
|---|---|---|
| Sprint 1 — Base funcional | 20/10 al 29/10 | T-02 autenticación y roles · T-03 despliegue · T-05 datos ficticios · HU-07, HU-08 · HU-14 básica · HU-12 básica |
| Sprint 2 — Datos reales y asignaciones | 30/10 al 08/11 | HU-16, HU-17 (la carga inicial se registra con el mismo servicio de operaciones) · HU-03 |
| Sprint 3 — Consultas y cierre | 09/11 al 16/11 | HU-12 completa · HU-10 · HU-11 · T-04 pruebas de aceptación · despliegue final |

## Riesgo que introduce y mitigación

Hasta el Sprint 2 el sistema funciona solo con datos ficticios, y no reemplaza
todavía a los archivos. La mitigación es que las cantidades de partida ya se
registran como operaciones (tipo «Carga inicial»), y HU-16 va a usar exactamente
ese mecanismo. La importación no requiere rehacer lo construido.
