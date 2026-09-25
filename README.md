# Evaluador de Agroquímicos

Aplicación Streamlit para revisar fichas técnicas y fichas de datos de seguridad de agroquímicos, identificar evidencia documental del ingrediente activo y contrastarla con criterios de plaguicidas de **RSPO** e **ISCC**. Las listas de **Rainforest Alliance (RA)** se usan como base local de detección y referencia complementaria.

**Aplicación web:** https://evaluador-agroquimicos.streamlit.app/


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

## Cómo interpretar los resultados

La aplicación separa **coincidencias normativas confirmadas**, **alertas que requieren revisión** y **limitaciones documentales**. El estado mostrado depende de la identidad del ingrediente, el contexto en que aparece en los PDF y la correspondencia explícita implementada para cada estándar.

| Resultado | Qué significa |
| --- | --- |
| `NO UTILIZAR — RSPO E ISCC` | Existe evidencia suficiente de que el ingrediente activo coincide con un criterio de prohibición explícito tanto en RSPO como en ISCC. |
| `NO UTILIZAR — RSPO` | Existe evidencia suficiente y el criterio está prohibido explícitamente por RSPO. La aplicación no afirma automáticamente que también esté prohibido por ISCC. |
| `ATENCIÓN — PROHIBIDO EN RA; REVISAR RSPO / ISCC` | Rainforest Alliance incluye el ingrediente en su lista de prohibidos, pero el criterio detectado no basta por sí solo para afirmar una prohibición equivalente en RSPO o ISCC. Requiere revisión específica. |
| `ATENCIÓN — PLAGUICIDA OBSOLETO SEGÚN RA` | Rainforest Alliance clasifica el ingrediente como obsoleto. Se conserva como alerta complementaria y debe revisarse frente al estándar aplicable y la normativa nacional. |
| `ATENCIÓN — MITIGACIÓN DE RIESGOS SEGÚN RA` | Rainforest Alliance exige medidas de mitigación para ese ingrediente. La alerta no se convierte automáticamente en una prohibición RSPO o ISCC. |
| `COINCIDENCIA NORMATIVA — REVISAR` | Se encontró una coincidencia real por CAS, nombre o grupo, pero no se confirmó automáticamente que corresponda al ingrediente activo o que la pertenencia normativa sea concluyente. |
| `REVISIÓN DOCUMENTAL` | El documento no pudo evaluarse con suficiente confiabilidad, por ejemplo porque carece de texto extraíble. No debe interpretarse como ausencia de riesgo. |
| `SIN COINCIDENCIAS DETECTADAS` | No se identificaron coincidencias con las listas y reglas implementadas a partir de la información disponible en los documentos analizados. |

Los estados `NO UTILIZAR` requieren evidencia documental suficiente del ingrediente activo; una mera mención incidental, una referencia bibliográfica, una negación o un producto de descomposición no debe producir por sí sola una decisión fuerte.

`SIN COINCIDENCIAS DETECTADAS` describe únicamente el resultado del análisis de los documentos cargados y de las reglas disponibles; no constituye una autorización regulatoria del producto.

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
