# Evaluador de Agroquímicos

Aplicación Streamlit para revisar fichas técnicas y fichas de datos de seguridad de agroquímicos, identificar evidencia documental del ingrediente activo y contrastarla con criterios de plaguicidas de **RSPO** e **ISCC**. Las listas de **Rainforest Alliance (RA)** se usan como base local de detección y referencia complementaria.

## Cómo funciona

1. Extrae texto de uno o varios PDF.
2. Detecta y valida números CAS.
3. Cruza CAS, nombres y grupos contra las listas locales.
4. Clasifica el contexto de cada coincidencia para distinguir ingrediente activo de menciones incidentales, negadas, de descomposición o de referencia.
5. Muestra la evidencia encontrada y su lectura frente a RSPO, ISCC y RA.

La evaluación es local y determinística. No consulta servicios externos para decidir el resultado.

## Criterios considerados

### RSPO
Fuente oficial: [RSPO Principles and Criteria 2024 v4.2 — español](https://rspo.org/wp-content/uploads/SPA-2024-RSPO-Principles-and-Criteria-%E2%80%93-Version-4.2-spanish.pdf)

Mapeo basado en RSPO P&C 2024 v4.2, indicador 7.1.2 (C):
- OMS 1A / 1B.
- Carcinogenicidad, mutagenicidad o toxicidad reproductiva SGA 1A / 1B.
- Convenios de Estocolmo o Rotterdam.
- Paraquat.

Las restricciones o prohibiciones nacionales deben verificarse aparte.

### ISCC
Fuente oficial: [ISCC EU 202-2 Agricultural Biomass: ISCC Principles 2-6](https://iscc-system.org/wp-content/uploads/dlm_uploads/2026/03/ISCC-EU-202-2-Agricultural-Biomass-ISCC-Principles-2-6.pdf)

Mapeo basado en **ISCC EU 202-2 v1.1** (válido desde el 1 de diciembre de 2022), requisito 2.4.1:
- OMS 1a / 1b.
- Convenio de Estocolmo.
- Anexo III del Convenio de Rotterdam.

La aplicación no traslada automáticamente a ISCC otros criterios de Rainforest Alliance.

### Rainforest Alliance
Fuente oficial: [Anexo al capítulo Agricultura v1.4](https://knowledge.rainforest-alliance.org/docs/es/farming-annex-v14)

Se conservan como referencia complementaria las listas locales de:
- PROHIBIDOS.
- OBSOLETOS.
- MITIGACIÓN DE RIESGOS.

Una clasificación de RA solo se traslada a RSPO o ISCC cuando existe una correspondencia explícita implementada.

## Resultados

- `NO UTILIZAR — RSPO E ISCC`
- `NO UTILIZAR — RSPO`
- `ATENCIÓN — PROHIBIDO EN RA; REVISAR RSPO / ISCC`
- `ATENCIÓN — PLAGUICIDA OBSOLETO SEGÚN RA`
- `ATENCIÓN — MITIGACIÓN DE RIESGOS SEGÚN RA`
- `COINCIDENCIA NORMATIVA — REVISAR`
- `REVISIÓN DOCUMENTAL`
- `SIN COINCIDENCIAS DETECTADAS`

Un resultado sin coincidencias se limita a la información disponible en los documentos analizados y a las reglas implementadas.

## Datos locales

- `data/master_restrictions.csv`: PROHIBIDOS.
- `data/obsolete.csv`: OBSOLETOS.
- `data/risk_mitigation.csv`: MITIGACIÓN DE RIESGOS.

Las reglas de correspondencia entre estándares están en `src/rules.py`.

## PubChem

Los CAS visibles pueden abrir PubChem como referencia manual. PubChem no participa en la evaluación ni modifica el resultado.

## Ejecución local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Pruebas

```bash
python -m unittest discover -s tests -v
```

La herramienta apoya el tamizaje documental y la trazabilidad. La decisión final debe considerar el estándar aplicable, la normativa nacional y cualquier excepción vigente.
