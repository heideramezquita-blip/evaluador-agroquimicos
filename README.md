# Evaluador de Agroquímicos — PROHIBIDOS

Aplicación Streamlit determinística para detectar evidencia documental contra la lista corporativa **PROHIBIDOS**.

## Flujo actual

1. Extrae texto de uno o varios PDF con PyMuPDF.
2. Canal CAS: detecta variantes de formato, canonicaliza, valida checksum, deduplica y cruza contra PROHIBIDOS.
3. Canal nombre/grupo: búsqueda conservadora de nombres y reglas explícitas para los 8 registros con CAS `varios`.
4. Solo después de una coincidencia clasifica su contexto local.
5. Resultados:
   - `NO UTILIZAR`: evidencia suficiente de ingrediente activo incluido en PROHIBIDOS.
   - `COINCIDENCIA CON PROHIBIDOS — REVISAR`: existe un hit real, pero su rol o pertenencia requiere confirmación.
   - `REVISIÓN DOCUMENTAL`: el documento no permite una evaluación suficiente, por ejemplo un PDF sin texto extraíble.
   - `SIN COINCIDENCIAS CON PROHIBIDOS`: no se encontraron coincidencias mediante los mecanismos disponibles.

La ausencia de coincidencias no significa que el producto sea seguro, permitido, autorizado o apto.

## Fuente de decisión

`data/master_restrictions.csv` contiene **exclusivamente la normalización de la hoja PROHIBIDOS** de SGA.PRO.14 usada por esta aplicación. Las demás hojas del Excel corporativo no forman parte de este repositorio ni de la lógica de decisión.

## Dependencias

El flujo normal no utiliza PubChem ni servicios externos.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

Auditoría del corpus, cuando está disponible localmente:

```bash
python scripts/audit_corpus.py /ruta/al/corpus docs
python scripts/audit_corpus.py /ruta/al/corpus pairs
```
