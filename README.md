# Evaluador de Agroquímicos

Aplicación Streamlit de evaluación determinística **CAS-first** para fichas técnicas y hojas de datos de seguridad (SDS/FDS).

## Flujo principal

1. Leer uno o varios PDF en memoria con PyMuPDF.
2. Extraer **todos** los patrones CAS detectables en el texto.
3. Normalizar guiones/espacios, validar el dígito de control y eliminar duplicados.
4. Comparar todos los CAS válidos contra `data/master_restrictions.csv`.
5. Aplicar la regla definida por la lista y por su alcance.
6. Si no se obtuvo ningún CAS del documento, intentar un fallback **secundario y conservador**: nombres expresamente rotulados como ingrediente activo → PubChem → CAS único.
7. El usuario puede introducir CAS manualmente en cualquier momento. Esos CAS pasan por la misma normalización, validación, base y reglas.

## Principios

- El sistema no necesita reconstruir toda la semántica de una FDS/FT para ejecutar el flujo principal.
- Todos los CAS encontrados se procesan internamente; la interfaz principal muestra solo el resultado y las coincidencias relevantes.
- La trazabilidad conserva archivo, página, contexto y origen de cada CAS.
- Una coincidencia CAS **no equivale automáticamente** a `NO UTILIZAR`.
- Si una lista exige confirmar que la sustancia es ingrediente activo, el motor intenta corroborarlo únicamente con evidencia explícita y local de los documentos; si no puede, deriva a `REVISIÓN MANUAL`.
- La ausencia de coincidencias restrictivas no se presenta como una afirmación general de seguridad o autorización.
- Un PDF sin texto extraíble no obliga a implementar OCR: se informa la limitación y queda disponible la entrada manual de CAS.

## Interpretación de la base

La base normalizada deriva de `Anexos. Manejo de plaguicidas.xlsx` (`SGA.PRO.14`, versión 01, 24/03/2026).

- `PROHIBITED`: coincidencia con *Plaguicidas prohibidos*. La hoja declara `Ingrediente activo o grupo`; por ello `NO UTILIZAR` solo se emite cuando el rol queda suficientemente confirmado.
- `MITIGATE_RISK`: coincidencia con *Plaguicidas para mitigar riesgo*. Se informa `REQUIERE MITIGACIÓN` cuando el rol queda confirmado; de lo contrario, `REVISIÓN MANUAL`.
- `OBSOLETE`: coincidencia con *Plaguicidas obsoletos (Ingrediente activo)*. El Excel no define por sí solo una regla automática equivalente a prohibición, por lo que queda en `REVISIÓN MANUAL`.
- `CARBAMATE` y `ORGANOPHOSPHATE`: listas nominales sin CAS en el Excel. Se conservan en la base normalizada como referencia, pero no intervienen en el cruce CAS automático.

## Evidencia auxiliar de ingrediente activo

La detección semántica se limita a nombres que el documento rotula expresamente como `Ingrediente activo` / `Ingredientes activos`. Esa evidencia **no controla la extracción CAS**. Solo se usa para:

1. corroborar el rol de un CAS que ya produjo una coincidencia en una regla dependiente del rol; y
2. intentar PubChem cuando no se detectó ningún CAS automático.

No se usa fuzzy matching químico. La asociación local CAS↔nombre exige proximidad sin otro CAS interpuesto, reduciendo el riesgo de atribuir a un coformulante el rol de un ingrediente activo vecino.

## Validación actual

La auditoría sobre el corpus real del proyecto evaluó 63 PDF y 30 pares FT/FDS. El detalle está en `validation/README.md` y en los CSV de esa carpeta.

Resultado directo, sin depender de PubChem:

- 59/63 PDF con texto extraíble suficiente.
- 23/30 pares (76,7 %) con al menos un CAS válido detectado directamente.
- 1 candidato CAS falso descartado por dígito de control.
- Los cuatro pares con coincidencias restrictivas del corpus fueron detectados y clasificados por la lógica de la base: 1 `NO UTILIZAR` y 3 `REQUIERE MITIGACIÓN`.

## Estructura

```text
evaluador-agroquimicos/
├── app.py
├── requirements.txt
├── data/
│   ├── master_restrictions.csv
│   └── README.md
├── src/
│   ├── cas_extractor.py
│   ├── cas_utils.py
│   ├── engine.py
│   ├── master_database.py
│   ├── models.py
│   ├── name_fallback.py
│   ├── pdf_reader.py
│   ├── pubchem.py
│   ├── rules.py
│   └── text_utils.py
├── scripts/
│   └── audit_corpus.py
├── tests/
└── validation/
```

## Ejecución local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Pruebas unitarias

```bash
python -m unittest discover -s tests -v
```

## Auditoría del corpus

```bash
python scripts/audit_corpus.py /ruta/al/corpus
```

El corpus no se incluye en el repositorio de la aplicación.
