# Evaluador de Agroquímicos — PROHIBIDOS

Aplicación Streamlit determinística para responder una pregunta acotada:

> ¿Existe evidencia documental suficiente de que el producto contiene como ingrediente activo una sustancia o grupo incluido en PROHIBIDOS?

## Flujo

1. Extrae texto de uno o varios PDF con PyMuPDF.
2. Canal CAS: extrae candidatos tolerando espacios, saltos de línea y guiones Unicode; canonicaliza; valida checksum; deduplica; cruza solo contra PROHIBIDOS con CAS específico.
3. Canal nombre/grupo: busca de forma conservadora nombres de PROHIBIDOS y reglas explícitas para los 8 registros cuyo CAS es `varios`.
4. Solo después de un hit clasifica un contexto local: `ACTIVE`, `COMPOSITION`, `INCIDENTAL`, `NEGATED`, `DECOMPOSITION_COMBUSTION`, `REFERENCE_TOXICOLOGY` o `UNCERTAIN`.
5. Emite únicamente `NO UTILIZAR`, `REVISIÓN MANUAL` o `SIN COINCIDENCIAS CON PROHIBIDOS`.

La ausencia de coincidencias no significa que el producto sea seguro, permitido, autorizado o apto para cualquier uso.

## Fuente de decisión

`data/master_restrictions.csv` conserva otras categorías por trazabilidad histórica, pero `ProhibitedDatabase` carga exclusivamente filas `source_list=PROHIBITED`. Ninguna otra lista modifica el resultado.

## Grupos con CAS = varios

Se tratan separadamente de los CAS específicos. Las reglas están en `src/prohibited_database.py`. Una coincidencia de grupo no se fuerza a `NO UTILIZAR` cuando la pertenencia no puede establecerse de forma determinística. En esos casos se utiliza `REVISIÓN MANUAL`.

## PubChem

No forma parte del flujo de producción y no se realizan consultas externas para decidir el resultado.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

Auditoría del corpus real, cuando el corpus está disponible localmente:

```bash
python scripts/audit_corpus.py /ruta/al/corpus docs
python scripts/audit_corpus.py /ruta/al/corpus pairs
```
