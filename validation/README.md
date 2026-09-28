# Validación histórica del corpus

Registro de la validación offline realizada sobre el corpus real suministrado durante el desarrollo del motor. Este archivo conserva resultados históricos; el contrato vigente de comportamiento está protegido por la suite de `tests/`.

Base histórica de validación antes de las pruebas externas adicionales:

- 63 PDF evaluados.
- 30 pares FT/FDS.
- Engeo: `NO UTILIZAR` por Tiametoxam.
- Mesamate: coincidencia con `Arsénico y sus compuestos` que requiere revisión.
- Domazon y Mezulfuron suplementario: documentos sin texto extraíble suficiente; requieren revisión documental.
- Las menciones incidentales identificadas en el benchmark (óxido de etileno, clordano, fosfina, cianuro de hidrógeno y ácido bórico) no se promueven automáticamente a `NO UTILIZAR`.

Los fixtures sintéticos permanecen en los tests y no se mezclan con las métricas del corpus real.

Nota: la interfaz actual separa una **coincidencia real con PROHIBIDOS** de una **limitación documental**, por lo que las etiquetas actuales son más específicas que las usadas en la primera auditoría histórica.


Los estados y conteos anteriores documentan el benchmark histórico y no deben usarse como contrato de salida de la versión actual ni como métrica de precisión sobre documentos nuevos. La suite en `tests/` contiene las regresiones vigentes que protegen esos casos y las correcciones posteriores del motor.
