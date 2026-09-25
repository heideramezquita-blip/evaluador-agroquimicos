# Bases locales

Este directorio contiene las listas normalizadas utilizadas por el evaluador:

- `master_restrictions.csv`: PROHIBIDOS.
- `obsolete.csv`: OBSOLETOS.
- `risk_mitigation.csv`: MITIGACIÓN DE RIESGOS.

Las listas provienen de la documentación corporativa basada en el Anexo al capítulo Agricultura de Rainforest Alliance y funcionan como base local de detección.

Los registros con CAS específico se consultan por CAS. Las entradas con CAS `varios` se tratan mediante reglas conservadoras en `src/prohibited_database.py`.

La correspondencia con criterios de RSPO e ISCC se define en `src/rules.py`. No se asume que toda clasificación de Rainforest Alliance sea automáticamente equivalente en esos estándares.

Si cambian las fuentes normativas, estas bases y las reglas de correspondencia deben revisarse antes de considerar actualizada la evaluación.
