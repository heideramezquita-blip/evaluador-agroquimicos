# Validación PROHIBIDOS

Validación offline de la arquitectura detector-first sobre el corpus real suministrado.

Base histórica de validación antes de las pruebas externas adicionales:

- 63 PDF evaluados.
- 30 pares FT/FDS.
- Engeo: `NO UTILIZAR` por Tiametoxam.
- Mesamate: coincidencia con `Arsénico y sus compuestos` que requiere revisión.
- Domazon y Mezulfuron suplementario: documentos sin texto extraíble suficiente; requieren revisión documental.
- Las menciones incidentales identificadas en el benchmark (óxido de etileno, clordano, fosfina, cianuro de hidrógeno y ácido bórico) no se promueven automáticamente a `NO UTILIZAR`.

Los fixtures sintéticos permanecen en los tests y no se mezclan con las métricas del corpus real.

Nota: la interfaz actual separa una **coincidencia real con PROHIBIDOS** de una **limitación documental**, por lo que las etiquetas actuales son más específicas que las usadas en la primera auditoría histórica.


Los estados anteriores documentan el benchmark histórico y no deben usarse como contrato de salida de la versión actual. La suite en `tests/` contiene las regresiones vigentes que protegen esos casos y las correcciones posteriores del motor.
