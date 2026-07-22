# P6-F.9.98 — Clinical KB Services Update

## Alcance

Actualización clínica determinista de KB_Servicios con información aprobada por la Dra. Paola D’Aleman.

No se modificaron PostgreSQL ni Google Sheets.

## Cambios principales

- Terapia Respiratoria actualizada:
  - activa;
  - domiciliaria;
  - sin orden médica previa;
  - duración aproximada de 30 a 45 minutos;
  - tres horas de ayuno.
- Oximetría Dinámica agregada como servicio independiente `SRV-07`.
- Oximetría Dinámica requiere:
  - orden médica;
  - validación previa;
  - revisión profesional cuando el paciente lleva 15 días o más con oxígeno.
- Traqueostomizados permanece inactivo.
- Oxigenoterapia domiciliaria no se ofrece.
- Curso Psicoprofiláctico Materno permanece retirado.
- Pruebas de función pulmonar, rehabilitación pulmonar y servicios empresariales actualizados.
- Se añadió un catálogo clínico aprobado como overlay de solo lectura.
- Texto y voz utilizan el mismo núcleo clínico determinista.
- Urgencias y opt-out conservan prioridad.

## Seguridad

La capa clínica no diagnostica, no prescribe y no confirma disponibilidad.

Una solicitud registrada continúa siendo una solicitud pendiente de confirmación.

## Validación

- Compilación Python correcta.
- Tests dirigidos: 11 passed.
- Suite completa: 431 passed.
- `git diff --check`: correcto.
