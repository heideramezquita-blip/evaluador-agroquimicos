# Base PROHIBIDOS normalizada

`master_restrictions.csv` contiene únicamente la hoja corporativa **Listado de plaguicidas prohibidos** normalizada desde **Anexos. Manejo de plaguicidas.xlsx** (`SGA.PRO.14`, versión `01`, fecha `2026-03-24`).

El encabezado de origen define las entradas como **Ingrediente activo o grupo**.

- Los registros con CAS específico se normalizan a una fila por CAS consultable.
- Si una entrada de origen contiene varios CAS, se expande sin cambiar el nombre, uso ni criterio.
- Los ocho registros cuyo CAS de origen es `varios`/no específico se conservan como grupos y se tratan mediante reglas explícitas y conservadoras.

No se incluyen aquí organofosforados, carbamatos, obsoletos ni la lista para mitigar riesgo porque no intervienen en el objetivo actual de la aplicación.

La mera aparición de una sustancia en un documento no se convierte automáticamente en `NO UTILIZAR`: el contexto determina si existe evidencia suficiente de ingrediente activo. Una coincidencia CAS exacta no confirmada se conserva como alarma para revisión.
