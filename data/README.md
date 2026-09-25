# Base maestra normalizada

`master_restrictions.csv` es una normalización del archivo corporativo **Anexos. Manejo de plaguicidas.xlsx**, identificado en las hojas de Anexo 1 y Anexo 2 como `SGA.PRO.14`, versión `01`, fecha `2026-03-24`.

La normalización conserva una fila por CAS consultable. Cuando una fila del Excel contiene varios CAS, se expande a varias filas sin cambiar el nombre/criterio de origen.

## Interpretación de listas

- `PROHIBITED`: la hoja se titula *Listado de plaguicidas prohibidos* y su encabezado dice **Ingrediente activo o grupo**. Acción operacional: `NO_UTILIZAR`, solo cuando el rol como ingrediente activo queda suficientemente confirmado.
- `MITIGATE_RISK`: la hoja se titula *Listado de plaguicidas para mitigar riesgo*. El Excel no indica expresamente que una coincidencia en cualquier coformulante deba activar la regla. Por ello se usa `ROLE_CONFIRMATION_REQUIRED`: con rol suficientemente confirmado se informa `REQUIERE_MITIGACION`; sin esa evidencia se deriva a `REVISIÓN MANUAL`.
- `OBSOLETE`: la hoja dice **PLAGUICIDAS OBSOLETOS (Ingrediente activo)**, pero el archivo no define por sí solo una acción equivalente a `NO_UTILIZAR`. Se conserva como `REVISAR_OBSOLETO`.
- `CARBAMATE` y `ORGANOPHOSPHATE`: son listas nominales sin CAS en el Excel. Se conservan como información de referencia (`NAME_ONLY`) y no intervienen en el cruce CAS automático.

La aplicación no interpreta la mera presencia de cualquier CAS como prohibición. Primero respeta la lista, acción y alcance normalizados de esta base.
