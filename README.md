# Evaluador de Agroquímicos

[![Licencia: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Aplicación Streamlit para realizar un **tamizaje documental de agroquímicos** frente a criterios de plaguicidas de **RSPO** e **ISCC**, utilizando las listas de **Rainforest Alliance (RA)** como base local de detección y referencia complementaria.

La aplicación detecta números CAS, coincidencias por nombre y determinadas reglas de grupo en los documentos cargados, clasifica el contexto de esas coincidencias y muestra la evidencia que sustenta el resultado. **No es un extractor químico universal ni sustituye una evaluación regulatoria completa.**

**Aplicación web:** https://evaluador-agroquimicos.streamlit.app/


## Entradas admitidas

La interfaz acepta:

- uno o varios archivos **PDF**;
- ficha técnica (FT), ficha de datos/hoja de seguridad (FDS/HS) o ambas para el mismo producto;
- opcionalmente, uno o varios números CAS introducidos manualmente.

> **Una evaluación corresponde a un producto.** La carga múltiple está pensada para combinar FT, FDS/HS u otros PDF del **mismo producto**. No deben mezclarse documentos de productos diferentes en una sola evaluación, porque el motor consolida los hallazgos documentales y produce un único resultado para todo el conjunto cargado.

El ejemplo mostrado en la entrada manual es `4685-14-7` y se utiliza únicamente como ejemplo de formato.

Cuando se introduce un CAS manual, la interfaz permite confirmar explícitamente que corresponde a un **ingrediente activo**. Sin esa confirmación, una coincidencia normativa por CAS no se convierte automáticamente en una decisión fuerte y se presenta para revisión.

La aplicación no incorpora OCR. Si un PDF está escaneado o no contiene texto extraíble suficiente, el resultado es `REVISIÓN DOCUMENTAL`; no se interpreta como ausencia de coincidencias.


## Cómo funciona

1. Extrae el texto disponible de uno o varios PDF, priorizando el orden visual/espacial del contenido para reducir desorden en tablas y bloques maquetados.
2. Ejecuta un **tamizaje dirigido desde las bases locales hacia el documento**: busca los CAS específicos, nombres/sinónimos normalizados y reglas de grupo configuradas en las listas de referencia. La evaluación normativa no depende de reconstruir previamente el ingrediente activo completo del producto.
3. Detecta números CAS y valida su checksum; evita interpretar como CAS fragmentos de identificadores químicos más largos, como determinados números INDEX.
4. Clasifica el contexto de cada coincidencia para distinguir, entre otros casos, **ingrediente activo**, **composición**, **identidad explícita del producto** (`Product name`, `Identificador del producto`, `Otros medios de identificación`), menciones incidentales, negadas, de descomposición/combustión o de referencia toxicológica. Las coincidencias en contextos confirmatorios pueden sostener una decisión; las menciones no confirmatorias se conservan para trazabilidad sin gobernar el resultado.
5. En paralelo, extrae **ingredientes activos identificados explícitamente por el documento** y, cuando es posible, sus CAS/concentraciones; también extrae por separado componentes de composición estructurados. Esta capa es **auxiliar y descriptiva**: sirve para presentar y enriquecer la identidad documental, pero no crea, oculta ni filtra las coincidencias normativas encontradas por el tamizaje dirigido.
6. Aplica las reglas de decisión y las correspondencias explícitas implementadas para RSPO, ISCC y RA. La tarjeta principal muestra primero la **coincidencia normativa realmente encontrada** o, cuando no existe una coincidencia relevante, el **alcance del tamizaje dirigido**. La identidad documental detectada se muestra después como evidencia complementaria.
7. Consolida la evidencia encontrada para evitar tarjetas duplicadas cuando una misma sustancia se detecta por más de un mecanismo.

La evaluación es **determinística** y utiliza bases incluidas en el proyecto. No consulta servicios externos para decidir el resultado.

La identificación no pretende reconocer cualquier sustancia química existente. Las coincidencias por nombre y grupo se realizan contra los registros y reglas incluidos en las bases locales. Un CAS válido que aparezca en una parte incidental del documento tampoco se trata automáticamente como ingrediente activo.


## Arquitectura

La estructura se mantiene deliberadamente pequeña y separa responsabilidades sin introducir capas innecesarias:

- `app.py`: interfaz Streamlit y renderizado.
- `src/engine.py`: orquestación del análisis documental, carga de las bases locales, ejecución del tamizaje dirigido, consolidación de evidencia auxiliar y evaluación final.
- `src/pdf_reader.py`: extracción de texto en orden visual/espacial y diagnóstico de documentos sin contenido principal extraíble, incluidos archivos que solo exponen encabezados o pies repetidos.
- `src/active_ingredient_extractor.py`: extracción de ingredientes activos explícitamente identificados por la FT/FDS y confirmación conservadora de identidad en FDS mediante evidencia documental correlacionada, independiente de que exista una coincidencia normativa.
- `src/cas_utils.py` y `src/cas_extractor.py`: normalización, validación y extracción de CAS, incluida la reconstrucción conservadora de CAS cuyo dígito de checksum queda separado en otro bloque de una tabla PDF.
- `src/composition_extractor.py`: extracción descriptiva de componentes en tablas estructuradas de composición de FDS; no promueve por sí sola esos componentes a ingrediente activo.
- `src/context_classifier.py`: clasificación contextual por proximidad y normalización de variantes frecuentes de ingrediente activo, composición, identidad explícita del producto y contextos no confirmatorios.
- `src/prohibited_database.py`: carga de las tres bases locales y metadatos de búsqueda.
- `src/prohibited_detector.py`: núcleo del tamizaje dirigido por CAS, nombre/sinónimo y reglas de grupo. No depende del extractor de ingrediente activo; conserva todas las coincidencias y deja que el clasificador contextual y las reglas determinen su relevancia.
- `src/rules.py`: decisión final y correspondencias explícitas entre RA, RSPO e ISCC.
- `src/criteria_presentation.py`: interpretación estructurada de criterios y explicaciones mostradas al usuario.
- `src/evidence_presentation.py`: consolidación y etiquetado de evidencia sin alterar la decisión normativa.
- `src/ui_helpers.py`: generación de HTML seguro y utilidades puras de presentación reutilizadas por Streamlit; no participa en la decisión normativa.
- `src/ui_styles.py`: hoja de estilos estática de la interfaz Streamlit, separada del flujo de la aplicación.
- `src/normative_sources.py`: metadatos y enlaces oficiales mostrados en la interfaz; son referencias informativas y no participan en la decisión.

La lógica normativa no depende de servicios externos y los componentes de presentación no modifican el resultado del motor. La interfaz consume resultados ya calculados por `src/engine.py`; las funciones puras de HTML y filtrado visual se mantienen fuera de `app.py` para evitar mezclar presentación con reglas de decisión.


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
| `NO UTILIZAR — RSPO E ISCC` | Existe una coincidencia documental fuerte con una sustancia de la base cuyo criterio está prohibido explícitamente tanto por RSPO como por ISCC. |
| `NO UTILIZAR — RSPO` | Existe evidencia suficiente y el criterio está prohibido explícitamente por RSPO. La aplicación no afirma automáticamente que también esté prohibido por ISCC. |
| `ATENCIÓN — PROHIBIDO EN RA; REVISAR RSPO / ISCC` | Rainforest Alliance incluye la sustancia detectada en su lista de prohibidos, pero el criterio detectado no basta por sí solo para afirmar una prohibición equivalente en RSPO o ISCC. Requiere revisión específica. |
| `ATENCIÓN — PLAGUICIDA OBSOLETO SEGÚN RA` | Rainforest Alliance clasifica la sustancia detectada como plaguicida obsoleto. Se conserva como alerta complementaria y debe revisarse frente al estándar aplicable y la normativa nacional. |
| `ATENCIÓN — MITIGACIÓN DE RIESGOS SEGÚN RA` | Rainforest Alliance incluye la sustancia detectada en su lista de mitigación de riesgos. Su uso requiere las medidas adicionales que correspondan al criterio identificado; la alerta no se convierte automáticamente en una prohibición RSPO o ISCC. |
| `POSIBLE PROHIBICIÓN EN RA — REVISAR IDENTIDAD` | Existe una coincidencia con la lista PROHIBIDOS de Rainforest Alliance, pero todavía no se confirmó que la sustancia corresponda al ingrediente activo del producto. La severidad potencial se conserva sin presentar la prohibición como confirmada. |
| `POSIBLE PLAGUICIDA OBSOLETO SEGÚN RA — REVISAR IDENTIDAD` | Existe una coincidencia con la lista de plaguicidas obsoletos de Rainforest Alliance, pero falta confirmar el papel de la sustancia dentro del producto. |
| `MITIGACIÓN DE RIESGOS — REVISAR IDENTIDAD` | Existe una coincidencia con la lista de mitigación de riesgos de Rainforest Alliance, pero falta confirmar que corresponda al ingrediente activo antes de aplicar las medidas asociadas. |
| `COINCIDENCIA NORMATIVA — REVISAR` | Estado residual para coincidencias que requieren revisión y no pueden atribuirse con suficiente claridad a una de las categorías anteriores. |
| `REVISIÓN DOCUMENTAL` | El documento no pudo evaluarse con suficiente confiabilidad, por ejemplo porque carece de texto extraíble o no pudo leerse. No debe interpretarse como ausencia de riesgo. |
| `REVISIÓN — IDENTIDAD QUÍMICA NO CONFIRMADA` | Estado de respaldo cuando no hubo contenido documental o entrada manual suficiente para ejecutar el tamizaje dirigido. |
| `SIN COINCIDENCIAS DETECTADAS` | El tamizaje dirigido se ejecutó sobre texto extraíble y/o CAS manuales válidos y no encontró coincidencias por CAS, nombre/sinónimo normalizado o regla de grupo. Describe únicamente el contenido analizado; no demuestra la ausencia química de una sustancia que el documento no declare. |

Los estados fuertes requieren una coincidencia normativa en un **contexto confirmatorio** (ingrediente activo, composición o identidad explícita del producto). Una mera mención incidental, una referencia bibliográfica, una negación o un producto de descomposición no debe producir por sí sola una decisión fuerte.

El bloque principal de resultado muestra primero **qué coincidencia normativa sostuvo la evaluación**; si no existe una coincidencia relevante, muestra el alcance del tamizaje dirigido (entradas normativas y documentos con texto extraíble). La sección de identidad documental se mantiene aparte como información auxiliar.

`SIN COINCIDENCIAS DETECTADAS` se usa cuando la búsqueda dirigida pudo ejecutarse sobre al menos un documento con texto extraíble o sobre CAS manuales válidos y no encontró coincidencias en las listas locales. No significa que el producto esté químicamente libre de esas sustancias: significa que **no fueron detectadas en el contenido disponible**. Ninguno de estos estados constituye una autorización regulatoria del producto.


## Evidencia y trazabilidad

Cuando existe una coincidencia relevante, la salida muestra primero la sección **Evidencia relevante**, con la sustancia, lista, CAS, uso cuando está disponible, tipo de evidencia, documento, páginas más relevantes, criterio identificado y lectura por estándar.

A continuación, la sección **Identidad documental detectada** muestra los ingredientes activos que la FT/FDS identifica explícitamente, incluso cuando no existe CAS asociado o cuando el ingrediente no aparece en las bases locales. Cuando una FDS declara una mezcla mediante una tabla estructurada de composición, la interfaz puede mostrar además **Componentes de composición detectados** con nombre, CAS y concentración. Estos componentes no se consideran automáticamente ingredientes activos, porque una FDS puede incluir solventes, sales, neutralizantes u otros componentes de formulación. Si otra evidencia del documento confirma el ingrediente activo, la composición puede utilizarse para completar su CAS o concentración.

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

Los archivos de `data/` se derivan de fuentes externas y **no quedan relicenciados automáticamente bajo MIT**. Consulte `data/README.md` y `THIRD_PARTY_NOTICES.md` antes de reutilizarlos o redistribuirlos.


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

La aplicación puede ejecutarse completamente en el propio computador. El navegador actúa únicamente como interfaz: el análisis de los PDF, la extracción de CAS, las reglas de decisión y las bases locales se ejecutan en la máquina donde se inicia Streamlit.

Una vez instaladas Python y las dependencias, el **tamizaje funciona sin conexión a Internet** porque no necesita consultar servicios externos para decidir el resultado. Sin conexión no estarán disponibles los enlaces externos de consulta, como PubChem o las fuentes normativas enlazadas.

### Windows · ejecución con doble clic

El repositorio incluye `Ejecutar_Windows.bat` para facilitar el uso local a personas que no quieran trabajar desde la terminal.

Requisitos:

1. Tener **Python 3** instalado en Windows.
2. Al instalar Python, conviene activar la opción **Add Python to PATH**.
3. Descargar o clonar este repositorio.
4. Hacer doble clic en `Ejecutar_Windows.bat`.

En el primer inicio, el archivo:

1. comprueba que Python esté disponible;
2. crea un entorno virtual local en `.venv`;
3. instala `streamlit` y `PyMuPDF` desde `requirements.txt` si todavía no están disponibles;
4. inicia `app.py` mediante Streamlit;
5. abre la interfaz en el navegador, normalmente en `http://localhost:8501`.

Los siguientes inicios reutilizan el mismo entorno virtual y no necesitan reinstalar las dependencias mientras sigan disponibles. Para detener la aplicación basta con cerrar la ventana de consola que la inició o pulsar `Ctrl+C`.

La **primera instalación** de dependencias sí requiere acceso a Internet. Después, la aplicación puede utilizarse localmente sin conexión para el análisis documental.

### Ejecución manual

Para quienes prefieran controlar el entorno desde la terminal:

```bash
python -m venv .venv
```

En Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

En macOS o Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

La versión local y la versión desplegada en Streamlit utilizan el **mismo motor de evaluación y las mismas bases incluidas en el repositorio**.


## Pruebas

```bash
python -m unittest discover -s tests -v
```

La suite incluye regresiones del motor, clasificación contextual, interpretación de criterios, presentación de evidencia, coherencia documental y un smoke test de Streamlit en CI.


## Autoría y asistencia de IA

**Autor y mantenedor:** Heider Amézquita.

Este proyecto fue desarrollado con asistencia técnica de **ChatGPT de OpenAI**, utilizado de forma activa para la generación, revisión, refactorización y documentación del código. La definición del problema, los criterios funcionales, la selección y organización de fuentes, la validación de resultados y las decisiones finales sobre el comportamiento de la herramienta corresponden al autor del proyecto.


## Licencia

El **código fuente y la documentación original del proyecto** se distribuyen bajo la [licencia MIT](LICENSE).

Copyright © 2026 Heider Amézquita.

La licencia MIT no pretende relicenciar materiales, normas, marcas, listas ni datos pertenecientes a terceros. Los archivos derivados de fuentes externas, en particular los contenidos de `data/`, deben utilizarse respetando las condiciones aplicables de sus fuentes originales. Consulte [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

El software se proporciona sin garantía y sus resultados deben interpretarse dentro de las limitaciones documentadas en este README.


## Cómo citar este proyecto

El repositorio incluye un archivo [`CITATION.cff`](CITATION.cff) para que GitHub y gestores compatibles generen la cita automáticamente.

Cita recomendada:

> Amézquita, H. (2026). *Evaluador de Agroquímicos* [Software]. GitHub. https://github.com/heideramezquita-blip/evaluador-agroquimicos

**Proyecto:** Evaluador de Agroquímicos  
**Autor:** Heider Amézquita  
**Repositorio:** https://github.com/heideramezquita-blip/evaluador-agroquimicos  
**Aplicación:** https://evaluador-agroquimicos.streamlit.app/
