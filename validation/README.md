# Validación PROHIBIDOS

Validación offline de la arquitectura detector-first sobre el corpus real suministrado.

- 63 PDF evaluados.
- 30 pares FT/FDS.
- Resultado por pares: 1 `NO UTILIZAR`, 3 `REVISIÓN MANUAL`, 26 `SIN COINCIDENCIAS CON PROHIBIDOS`.
- Engeo: `NO UTILIZAR` por Tiametoxam.
- Mesamate: `REVISIÓN MANUAL` por evidencia de pertenencia a `Arsénico y sus compuestos`; no se permite falso negativo silencioso.
- Domazon: `REVISIÓN MANUAL` porque FT/FDS son escaneadas y no tienen texto extraíble suficiente.
- Mezulfuron suplementario: `REVISIÓN MANUAL` por la misma limitación documental.
- Los hits incidentales reales (óxido de etileno, clordano, fosfina, cianuro de hidrógeno y ácido bórico en los contextos identificados) no producen `NO UTILIZAR`.

En evaluación individual de los 63 PDF: 1 `NO UTILIZAR`, 6 `REVISIÓN MANUAL` y 56 `SIN COINCIDENCIAS CON PROHIBIDOS`.

Los fixtures sintéticos se mantienen en los tests y no se mezclan con las métricas del corpus.
