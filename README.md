# Evaluador de Agroquímicos

Aplicación Streamlit determinística para revisar fichas técnicas y fichas de datos de seguridad de agroquímicos, identificar evidencia documental del ingrediente activo y contrastarla con criterios de plaguicidas de **RSPO** e **ISCC**, conservando las listas de **Rainforest Alliance (RA)** como base local de detección y referencia complementaria.

La aplicación no pretende sustituir una revisión normativa completa ni certificar por sí sola que un producto esté permitido. Su función es automatizar el tamizaje documental, hacer trazable la evidencia encontrada y separar las coincidencias fuertes de las que requieren revisión humana.

## Prioridad normativa

La lectura de resultados prioriza actualmente:

1. **RSPO — Principios y Criterios 2024 v4.2, indicador 7.1.2 (C)**
   - OMS 1A / 1B.
   - Carcinogenicidad, mutagenicidad o toxicidad reproductiva SGA 1A / 1B.
   - Convenios de Estocolmo o Rotterdam.
   - Paraquat.
   - Las restricciones o prohibiciones nacionales deben verificarse aparte.

2. **ISCC EU**
   - ISCC EU 201 v4.2 remite los requisitos de biomasa agrícola a ISCC EU 202-2.
   - El mapeo local implementado utiliza los criterios explícitos verificados en 202-2 §2.4.1: OMS 1a / 1b, Convenio de Estocolmo y Anexo III del Convenio de Rotterdam.

3. **Rainforest Alliance**
   - Se mantienen las listas locales de **PROHIBIDOS**, **OBSOLETOS** y **MITIGACIÓN DE RIESGOS** del Anexo al capítulo Agricultura v1.4 como fuente de detección.
   - Una clasificación de RA no se convierte automáticamente en una prohibición RSPO o ISCC cuando no existe correspondencia explícita codificada.

El cruce entre estándares es deliberadamente conservador: la aplicación solo traslada un criterio de RA a RSPO o ISCC cuando existe una correspondencia normativa explícita implementada en `src/rules.py`.

## Cómo funciona

1. Extrae texto de uno o varios PDF con PyMuPDF.
2. Detecta candidatos CAS tolerando variaciones comunes de formato.
3. Canonicaliza los CAS, valida su checksum y elimina duplicados.
4. Cruza los CAS válidos contra las listas locales.
5. Ejecuta un canal complementario por nombre o grupo, con reglas explícitas para entradas cuyo CAS es `varios`.
6. Clasifica el contexto de cada coincidencia para distinguir, entre otros:
   - ingrediente activo,
   - composición,
   - mención incidental,
   - negación,
   - producto de descomposición/combustión,
   - referencia toxicológica.
7. Solo las coincidencias con evidencia contextual suficiente pueden producir una decisión fuerte.
8. Presenta la evidencia, documento, página, canal de detección, contexto y lectura por estándar.

No se utiliza un modelo generativo ni una búsqueda semántica externa para decidir si un producto coincide con las listas.

## Resultados principales

- `NO UTILIZAR — RSPO E ISCC`: existe evidencia suficiente del ingrediente activo y el criterio detectado está mapeado explícitamente en ambos estándares.
- `NO UTILIZAR — RSPO`: existe evidencia suficiente y el criterio está mapeado explícitamente en RSPO, pero no se traslada automáticamente a ISCC.
- `ATENCIÓN — PROHIBIDO EN RA; REVISAR RSPO / ISCC`: RA clasifica el ingrediente como prohibido, pero el criterio encontrado no demuestra por sí solo una prohibición equivalente en RSPO o ISCC.
- `ATENCIÓN — PLAGUICIDA OBSOLETO SEGÚN RA`: alerta complementaria basada en la lista de obsoletos de RA.
- `ATENCIÓN — MITIGACIÓN DE RIESGOS SEGÚN RA`: alerta complementaria basada en la lista de mitigación de riesgos de RA.
- `COINCIDENCIA NORMATIVA — REVISAR`: existe una coincidencia real, pero no se confirmó automáticamente su papel como ingrediente activo o su pertenencia normativa.
- `REVISIÓN DOCUMENTAL`: uno o más documentos no tienen texto extraíble suficiente para una evaluación confiable.
- `SIN COINCIDENCIAS DETECTADAS`: no se encontraron coincidencias mediante los mecanismos disponibles en los documentos analizados.

Un resultado sin coincidencias se limita a los documentos cargados y a las reglas implementadas.

## Datos locales

La aplicación carga tres archivos normalizados:

- `data/master_restrictions.csv`: 165 registros de **PROHIBIDOS**.
- `data/obsolete.csv`: 24 registros de **OBSOLETOS**.
- `data/risk_mitigation.csv`: 168 registros de **MITIGACIÓN DE RIESGOS**.

Las listas fueron normalizadas a partir de la documentación corporativa basada en el Anexo al capítulo Agricultura de Rainforest Alliance. La fecha de la carga local se informa también dentro de la interfaz.

Los registros con CAS específico se consultan por CAS. Las entradas de grupo con CAS `varios` se procesan mediante reglas conservadoras definidas en `src/prohibited_database.py`; una coincidencia nominal ambigua no se convierte por sí sola en una decisión fuerte.

## PubChem y servicios externos

**La evaluación no consulta PubChem ni ningún otro servicio externo.**

Cuando un CAS concreto es visible en la interfaz, puede mostrarse como enlace hacia PubChem únicamente para que el usuario abra una referencia manual en otra pestaña. Ese enlace no modifica, complementa ni participa en la decisión del evaluador.

Por tanto, el mismo conjunto de documentos y la misma base local producen el mismo resultado aunque PubChem no esté disponible.

## Pruebas automatizadas

Las pruebas unitarias están en `tests/` y verifican reglas concretas del motor: detección de CAS, contexto, listas, mapeo RSPO/ISCC y regresiones conocidas.

Para ejecutarlas:

```bash
python -m unittest discover -s tests -v
```

Además, el repositorio tiene un workflow de GitHub Actions que, en cada cambio a `main` y en cada pull request:

1. instala las dependencias;
2. ejecuta las pruebas unitarias;
3. compila `app.py`, `src/*.py` y `scripts/*.py`;
4. inicia Streamlit y comprueba su endpoint de salud.

Esto permite detectar errores de importación, sintaxis y regresiones básicas antes de considerar estable un cambio.

## Qué significa «corpus»

En este proyecto, **corpus** significa simplemente un conjunto organizado de PDF reales —por ejemplo fichas técnicas y hojas de seguridad— utilizado para probar el comportamiento del evaluador con documentos del mundo real.

No es una base que «entrene» la aplicación y tampoco forma parte de la evaluación de un usuario en producción. Sirve como conjunto de validación.

El script `scripts/audit_corpus.py` puede evaluar ese conjunto de dos maneras:

### Documento por documento

```bash
python scripts/audit_corpus.py /ruta/al/corpus docs
```

Genera `validation_corpus_documents.csv` con, entre otros, el archivo, estado, capacidad de extracción de texto, CAS válidos y coincidencias detectadas.

### Por producto: FT + HS

```bash
python scripts/audit_corpus.py /ruta/al/corpus pairs
```

El script espera, cuando existen, carpetas:

```text
corpus/
├── FT/
├── HS/
├── SFT/
└── SHS/
```

Los documentos se emparejan mediante el identificador numérico al inicio del nombre de archivo. Por ejemplo, una FT que empieza por `17.` y una HS que empieza por `17.` se evalúan juntas como el mismo producto.

La auditoría del corpus registra **qué respondió el motor**. Por sí sola no demuestra que esa respuesta sea correcta. Para medir falsos positivos, falsos negativos o regresiones se necesita un *ground truth* o benchmark previamente revisado.

## Ejecución local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Diseño y límites

- Evaluación local y determinística.
- Sin consultas externas durante la decisión.
- CAS exacto validado tiene mayor peso que coincidencias nominales.
- Las menciones incidentales, negadas, de descomposición o de referencia se mantienen fuera de decisiones fuertes.
- Los grupos químicos amplios no se resuelven por inferencia química abierta: requieren una regla explícita o revisión humana.
- Un PDF sin texto extraíble no se interpreta como resultado negativo.
- Las restricciones nacionales y las excepciones particulares de cada estándar no se infieren automáticamente.
- La base normativa local debe actualizarse cuando cambien las fuentes aplicables.

La aplicación es una herramienta de apoyo para evaluación documental y trazabilidad; la decisión final debe considerar el estándar aplicable, la normativa nacional y cualquier excepción o condición vigente.
