# Bases locales

Este directorio contiene las listas normalizadas utilizadas por el evaluador:

- `master_restrictions.csv`: PROHIBIDOS.
- `obsolete.csv`: OBSOLETOS.
- `risk_mitigation.csv`: MITIGACIÓN DE RIESGOS.
- `chemical_substances.csv`: identidades químicas normalizadas y relaciones estructurales explícitas.
- `chemical_aliases.csv`: nombres regulatorios ES, nombres canónicos inglés/internacional e IUPAC utilizados por el matcher.

Las listas locales se normalizaron a partir del Anexo al capítulo Agricultura de Rainforest Alliance y funcionan como base de detección.

Los registros con CAS específico se consultan por CAS. Las entradas sin CAS específico representan grupos o familias y se tratan mediante reglas conservadoras en `src/prohibited_database.py`; en la interfaz pueden mostrarse como `Varios`.

La correspondencia con criterios de RSPO e ISCC se define en `src/rules.py`. No se asume que toda clasificación de Rainforest Alliance sea automáticamente equivalente en esos estándares.

Si cambian las fuentes normativas, estas bases y las reglas de correspondencia deben revisarse antes de considerar actualizada la evaluación.

El registro químico se genera mediante `../scripts/enrich_chemical_aliases.py`. Los nombres canónicos e IUPAC se consultan por CAS mediante PubChem PUG REST únicamente durante mantenimiento; la aplicación no depende de PubChem en tiempo de evaluación. No se importa de forma indiscriminada el catálogo completo de sinónimos de PubChem.


## Reutilización y licencia

Estos archivos fueron normalizados a partir de fuentes externas. La licencia MIT del código fuente del proyecto **no relicencia automáticamente estos datos ni los materiales originales de terceros**.

Antes de copiar, redistribuir o incorporar estas listas en otro producto, revise las condiciones de uso aplicables de las fuentes originales y conserve las atribuciones que correspondan. Consulte también `../THIRD_PARTY_NOTICES.md`.
