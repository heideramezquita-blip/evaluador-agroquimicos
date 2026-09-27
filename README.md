# Evaluador de Agroquímicos

Aplicación Streamlit para realizar un **tamizaje documental de agroquímicos** frente a criterios de plaguicidas de **RSPO** e **ISCC**, utilizando las listas de **Rainforest Alliance (RA)** como base local de detección y referencia complementaria.

La aplicación detecta números CAS, coincidencias por nombre y determinadas reglas de grupo en los documentos cargados, clasifica el contexto de esas coincidencias y muestra la evidencia que sustenta el resultado. **No es un extractor químico universal ni sustituye una evaluación regulatoria completa.**

**Aplicación web:** https://evaluador-agroquimicos.streamlit.app/


## Entradas admitidas

La interfaz acepta:

- uno o varios archivos **PDF**;
- ficha técnica (FT), ficha de datos/hoja de seguridad (FDS/HS) o ambas para el mismo producto;
- opcionalmente, uno o varios números CAS introducidos manualmente.

El ejemplo mostrado en la entrada manual es `4685-14-7` y se utiliza únicamente como ejemplo de formato.

Cuando se introduce un CAS manual, la interfaz permite confirmar explícitamente que corresponde a un **ingrediente activo**. Sin esa confirmación, una coincidencia normativa por CAS no se convierte automáticamente en una decisión fuerte y se presenta para revisión.

La aplicación no incorpora OCR. Si un PDF está escaneado o no contiene texto extraíble suficiente, el resultado es `REVISIÓN DOCUMENTAL`; no se interpreta como ausencia de coincidencias.


## Cómo funciona

1. Extrae el texto disponible de uno o varios PDF, priorizando el orden visual/espacial del contenido para reducir desorden en tablas y bloques maquetados.
2. Detecta números CAS y valida su checksum; evita interpretar como CAS fragmentos de identificadores químicos más largos, como determinados números INDEX.
3. Cruza CAS, nombres normalizados y determinadas reglas de grupo contra las tres bases locales.
4. Clasifica el contexto de cada coincidencia para distinguir, entre otros casos, ingrediente activo, composición, menciones incidentales, negadas, de descomposición/combustión o de referencia toxicológica. La clasificación admite variantes frecuentes de encabezados de FT/FDS y pondera la proximidad entre el nombre/CAS encontrado y el encabezado que le da contexto.
5. Aplica las reglas de decisión y las correspondencias explícitas implementadas para RSPO, ISCC y RA.
6. Consolida la evidencia encontrada para evitar tarjetas duplicadas cuando una misma sustancia se detecta por más de un mecanismo.

La evaluación es **determinística** y utiliza bases incluidas en el proyecto. No consulta servicios externos para decidir el resultado.

La identificación no pretende reconocer cualquier sustancia química existente. Las coincidencias por nombre y grupo se realizan contra los registros y reglas incluidos en las bases locales. Un CAS válido que aparezca en una parte incidental del documento tampoco se trata automáticamente como ingrediente activo.


## Arquitectura

La estructura se mantiene deliberadamente pequeña y separa responsabilidades sin introducir capas innecesarias:

- `app.py`: interfaz Streamlit y renderizado.
- `src/pdf_reader.py`: extracción de texto en orden visual/espacial y diagnóstico de documentos sin contenido principal extraíble, incluidos archivos que solo exponen encabezados o pies repetidos.
- `src/cas_utils.py` y `src/cas_extractor.py`: normalización, validación y extracción de CAS.
- `src/context_classifier.py`: clasificación contextual por proximidad y normalización de variantes frecuentes de encabezados de ingrediente activo y composición.
- `src/prohibited_database.py`: carga de las tres bases locales y metadatos de búsqueda.
- `src/prohibited_detector.py`: detección por CAS, nombre y reglas de grupo.
- `src/rules.py`: decisión final y correspondencias explícitas entre RA, RSPO e ISCC.
- `src/criteria_presentation.py`: interpretación estructurada de criterios y explicaciones mostradas al usuario.
- `src/evidence_presentation.py`: consolidación y presentación de evidencia sin alterar la decisión normativa.

La lógica normativa no depende de servicios externos y los componentes de presentación no modifican el resultado del motor.


## Criterios considerados

### RSPO

Fuente oficial: [RSPO Principles and Criteria 2024 v4.2 — español](https://rspo.org/wp-content/uploads/SPA-2024-RSPO-Principles-and-Criteria-%E2%80%93-Version-4.2-spanish.pdf)

Mapeo basado en RSPO P&C 2024 v4.2, indicador 7.1.2 (C):

- OMS Ia / Ib (también expresado como 1A / 1B en el documento).
- Carcinogenicidad, mutagenicidad o toxicidad reproductiva SGA 1A / 1B.
- Convenios de Estocolmo o Rotterdam.
- Paraquat.

Las restricciones o prohibiciones nacionales deben verificarse aparte.

### ISCC

Fuente oficial: [ISCC EU 202-2 Agricultural Biomass: ISCC Principles 2-6](https://iscc-system.org/wp-content/uploads/dlm_uploads/2026/03/ISCC-EU-202-2-Agricultural-Biomass-ISCC-Principles-2-6.pdf)

Mapeo basado en **ISCC EU 202-2 v1.1** (válido desde el 1 de diciembre de 2022), requisito 2.4.1:

- OMS Ia / Ib.
- Convenio de Estocolmo.
- Anexo III del Convenio de Rotterdam.

La aplicación no traslada automáticamente a ISCC otros criterios de Rainforest Alliance.

### Rainforest Alliance

Fuente oficial: [Anexo al capítulo Agricultura v1.4](https://knowledge.rainforest-alliance.org/docs/es/farming-annex-v14)

Las listas locales se utilizan como base de detección y referencia complementaria:

- **PROHIBIDOS**.
- **OBSOLETOS**.
- **MITIGACIÓN DE RIESGOS**.

**Última carga de la base local: septiembre de 2026.**

Una clasificación de RA solo se traslada a RSPO o ISCC cuando existe una correspondencia explícita implementada. Pertenecer a una lista de RA no equivale automáticamente a una prohibición en RSPO o ISCC.


## OMS y convenios internacionales

### OMS — clasificación de plaguicidas por peligrosidad

La publicación [*The WHO Recommended Classification of Pesticides by Hazard and guidelines to classification, 2019 edition*](https://www.who.int/publications/i/item/9789240005662) fue publicada en 2020 y reemplaza la edición 2009. La [ficha oficial en español](https://www.who.int/es/publications/i/item/9789240005662) registra correcciones posteriores en 2020 y 2021, sin señalar una edición sustitutiva posterior; consulta también el [PDF oficial](https://iris.who.int/server/api/core/bitstreams/36c193cd-2362-46d1-be00-fef570d80037/content). Clasifica la peligrosidad aguda para la salud humana en **Ia, Ib, II, III y U**.

La clasificación OMS es distinta del **SGA**: usa categorías OMS para la peligrosidad aguda de plaguicidas, mientras que las categorías SGA se interpretan dentro de cada clase de peligro. La OMS Ia/Ib no constituye por sí sola una prohibición legal ni una autorización regulatoria del producto.

### Protocolo de Montreal

El [Protocolo de Montreal sobre Sustancias que Agotan la Capa de Ozono](https://ozone.unep.org/treaties/montreal-protocol) controla sustancias que agotan la capa de ozono. En la aplicación, el marcador de Montreal se interpreta como un criterio de la fuente RA cuando está documentado en la base local; **no se convierte automáticamente en una prohibición RSPO o ISCC**.

### Convenio de Rotterdam

El [listado oficial del Anexo III](https://www.pic.int/theconvention/chemicals/annexiiichemicals) identifica sustancias sujetas al procedimiento de consentimiento fundamentado previo (PIC) en el comercio internacional. La [descripción oficial del procedimiento PIC](https://www.pic.int/en-us/procedures/picprocedure.aspx) explica el mecanismo; una referencia al Anexo III no debe leerse como una prohibición universal.

### Convenio de Estocolmo

El [listado oficial de contaminantes orgánicos persistentes (POP)](https://chm.pops.int/TheConvention/Thepops/Listingofpops/tabid/2509/Default.aspx) reúne sustancias incluidas en los anexos A, B y C. Las obligaciones dependen del anexo; están disponibles los listados oficiales de [Anexo A](https://chm.pops.int/Implementation/Alternatives/AlternativestoPOPs/ChemicalslistedinAnnexA/tabid/5837/Default.aspx) y [Anexo B](https://chm.pops.int/Implementation/Alternatives/AlternativestoPOPs/ChemicalslistedinAnnexB/tabid/5850/Default.aspx).

Estos enlaces son referencias documentales. La aplicación **no consulta las páginas en tiempo real, no importa automáticamente esas listas y no crea prohibiciones a partir de ellas**. Solo presenta una correspondencia de RSPO o ISCC cuando el criterio consta en la base local y esa equivalencia está expresamente implementada; las referencias no determinan por sí solas una prohibición legal nacional.


## Cómo interpretar los criterios de las listas

La interfaz utiliza las siguientes lecturas:

- **OMS Ia/Ib:** peligrosidad aguda para la salud humana; Ia significa extremadamente peligroso e Ib, altamente peligroso. Es un sistema distinto del SGA.
- **SGA 1A/1B:** la categoría debe leerse junto con la clase de peligro. Cuando están documentadas, la aplicación muestra las clases CMR: carcinogenicidad, mutagenicidad y toxicidad reproductiva.
- **Protocolo de Montreal:** trata sustancias que agotan la capa de ozono.
- **Rotterdam:** somete determinadas sustancias del Anexo III al procedimiento PIC en el comercio internacional; no significa una prohibición universal.
- **Estocolmo:** regula contaminantes orgánicos persistentes mediante eliminación (anexo A), restricción (anexo B) o reducción de liberaciones no intencionales (anexo C), según las condiciones y excepciones aplicables.
- **Efectos graves:** criterio de Rainforest Alliance por alta incidencia de efectos adversos graves o irreversibles sobre la salud humana o el ambiente.
- **Mitigación de riesgos:** Rainforest Alliance identifica plaguicidas cuyo uso requiere medidas adicionales para reducir riesgos específicos, por ejemplo para las personas, organismos acuáticos, vida silvestre o polinizadores. Su inclusión en esta lista no significa por sí sola que el plaguicida esté prohibido.

Rainforest Alliance se mantiene como referencia complementaria: su inclusión no equivale automáticamente a una prohibición de RSPO o ISCC.


## Cómo interpretar los resultados

La aplicación separa **coincidencias normativas confirmadas**, **alertas que requieren revisión** y **limitaciones documentales**. El estado mostrado depende de la identidad de la sustancia, el contexto en que aparece en los PDF y la correspondencia explícita implementada para cada estándar.

| Resultado | Qué significa |
| --- | --- |
| `NO UTILIZAR — RSPO E ISCC` | Existe evidencia suficiente de que el ingrediente activo coincide con un criterio de prohibición explícito tanto en RSPO como en ISCC. |
| `NO UTILIZAR — RSPO` | Existe evidencia suficiente y el criterio está prohibido explícitamente por RSPO. La aplicación no afirma automáticamente que también esté prohibido por ISCC. |
| `ATENCIÓN — PROHIBIDO EN RA; REVISAR RSPO / ISCC` | Rainforest Alliance incluye el ingrediente en su lista de prohibidos, pero el criterio detectado no basta por sí solo para afirmar una prohibición equivalente en RSPO o ISCC. Requiere revisión específica. |
| `ATENCIÓN — PLAGUICIDA OBSOLETO SEGÚN RA` | Rainforest Alliance clasifica el ingrediente como obsoleto. Se conserva como alerta complementaria y debe revisarse frente al estándar aplicable y la normativa nacional. |
| `ATENCIÓN — MITIGACIÓN DE RIESGOS SEGÚN RA` | Rainforest Alliance incluye el ingrediente en su lista de mitigación de riesgos. Su uso requiere las medidas adicionales que correspondan al criterio identificado; la alerta no se convierte automáticamente en una prohibición RSPO o ISCC. |
| `COINCIDENCIA NORMATIVA — REVISAR` | Se encontró una coincidencia real por CAS, nombre o grupo, pero no se confirmó automáticamente que corresponda al ingrediente activo o que la pertenencia normativa sea concluyente. |
| `REVISIÓN DOCUMENTAL` | El documento no pudo evaluarse con suficiente confiabilidad, por ejemplo porque carece de texto extraíble o no pudo leerse. No debe interpretarse como ausencia de riesgo. |
| `REVISIÓN — IDENTIDAD QUÍMICA NO CONFIRMADA` | El PDF tiene texto extraíble, pero no se identificó un CAS válido en contexto de ingrediente/composición ni una referencia explícita a ingrediente activo. Un encabezado de composición sin contenido químico extraíble no basta para sostener un resultado negativo. No debe interpretarse como que el producto está fuera de las listas. |
| `SIN COINCIDENCIAS DETECTADAS` | Sí existe información química utilizable para el tamizaje —por ejemplo, un CAS válido en contexto de ingrediente/composición, una referencia explícita a ingrediente activo/composición o un CAS manual válido— y no se identificaron coincidencias con las listas y reglas implementadas. |

Los estados `NO UTILIZAR` requieren evidencia documental suficiente del ingrediente activo; una mera mención incidental, una referencia bibliográfica, una negación o un producto de descomposición no debe producir por sí sola una decisión fuerte.

`SIN COINCIDENCIAS DETECTADAS` solo se usa cuando el sistema encontró alguna señal química utilizable para efectuar el tamizaje: por ejemplo, un CAS válido en contexto de ingrediente/composición, una referencia explícita a ingrediente activo o un CAS manual válido. Si el PDF es legible pero no aporta esa señal, se muestra `REVISIÓN — IDENTIDAD QUÍMICA NO CONFIRMADA`. Ninguno de estos estados constituye una autorización regulatoria del producto.


## Evidencia y trazabilidad

Cuando existe una coincidencia relevante, la aplicación muestra la sustancia, lista, CAS, uso cuando está disponible, tipo de evidencia, documento, páginas más relevantes, criterio identificado y lectura por estándar.

La sección **Detalles técnicos y trazabilidad** conserva información de auditoría, entre ella:

- tamaño de las tres bases locales;
- CAS válidos detectados;
- documentos analizados y si contienen texto extraíble;
- coincidencias candidatas evaluadas;
- candidatos CAS descartados por checksum cuando existen.

Una misma sustancia detectada por CAS y por nombre se consolida en una sola tarjeta de evidencia por lista, sustancia, CAS y documento.


## Datos locales

- `data/master_restrictions.csv`: PROHIBIDOS.
- `data/obsolete.csv`: OBSOLETOS.
- `data/risk_mitigation.csv`: MITIGACIÓN DE RIESGOS.

Las reglas de correspondencia entre estándares están en `src/rules.py`.


## PubChem

Los CAS visibles pueden abrir PubChem como referencia manual. PubChem no participa en la evaluación ni modifica el resultado.


## Limitaciones

- Solo se aceptan archivos PDF desde el cargador de la interfaz.
- No hay OCR integrado para documentos escaneados sin texto extraíble. Los PDF que solo permiten extraer el mismo encabezado o pie repetido, sin el contenido principal de las páginas, se tratan como documentación insuficiente y pasan a revisión documental.
- La detección por nombre y grupo depende de las sustancias y reglas incluidas en las bases locales; no es un reconocimiento químico abierto o universal.
- Las bases normativas son locales y deben actualizarse deliberadamente cuando cambien las fuentes.
- Las referencias oficiales enlazadas son informativas y no se consultan en tiempo real para tomar decisiones.
- Las restricciones nacionales, excepciones y condiciones específicas del estándar requieren verificación aparte.
- El resultado apoya el tamizaje y la trazabilidad documental; no constituye por sí solo una autorización regulatoria del producto.


## Ejecución local

```bash
pip install -r requirements.txt
streamlit run app.py
```


## Pruebas

```bash
python -m unittest discover -s tests -v
```

La suite incluye regresiones del motor, clasificación contextual, interpretación de criterios, presentación de evidencia, coherencia documental y un smoke test de Streamlit en CI.
