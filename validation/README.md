# Validación sobre el corpus real

La auditoría se ejecutó sobre el corpus suministrado para el proyecto.

## Resultado actual del motor CAS-first

- Documentos PDF evaluados: **63**.
- Documentos con texto extraíble suficiente: **59/63 (93,7 %)**.
- Documentos individuales con al menos un CAS válido detectado directamente: **25/63 (39,7 %)**.
- Pares FT/FDS evaluados: **30**.
- Pares con al menos un CAS válido detectado directamente en alguno de los dos documentos: **23/30 (76,7 %)**.
- Pares sin CAS automático directo: **7/30 (23,3 %)**.
- PDFs totalmente escaneados/no extraíbles dentro de esos pares: **2 pares** (Metsulfuron suplementario y Domazon).
- Candidatos con formato CAS descartados por dígito de control: **1** en todo el corpus (un número CE `613-167-00-5` del que la regex detecta `167-00-5`; se descarta correctamente).

## Resultados de reglas sobre los 30 pares

- `NO UTILIZAR`: **1** — Engeo, por CAS `153719-23-4` (Tiametoxam) en la lista de prohibidos.
- `REQUIERE MITIGACIÓN`: **3** — DeltaPoint, Malathion 57 EC y Numetrin EC.
- `SIN COINCIDENCIAS RESTRICTIVAS EN LAS LISTAS EVALUADAS`: **19**.
- `NO FUE POSIBLE DETERMINAR UN CAS AUTOMÁTICAMENTE`: **7**.

En Engeo también se detecta `91465-08-6` en la lista de mitigación; prevalece el resultado `NO UTILIZAR` por existir una coincidencia prohibida confirmada.

## Alcance de estas métricas

Estas cifras miden la extracción directa desde PDF y el cruce determinístico con la base. No incluyen el incremento potencial del fallback por PubChem, porque la auditoría del corpus se ejecutó sin depender de red externa. La entrada manual de CAS está cubierta por pruebas unitarias.

Los archivos CSV de esta carpeta conservan el detalle por documento y por pareja FT/FDS.
