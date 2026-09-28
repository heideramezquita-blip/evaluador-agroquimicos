"""Static official reference links for standards and conventions.

These links are informational only. The application does not fetch them at
runtime or use their contents to make evaluation decisions.
"""

RSPO_PNC_2024_ES = "https://rspo.org/wp-content/uploads/SPA-2024-RSPO-Principles-and-Criteria-%E2%80%93-Version-4.2-spanish.pdf"
ISCC_EU_202_2 = "https://iscc-system.org/wp-content/uploads/dlm_uploads/2026/03/ISCC-EU-202-2-Agricultural-Biomass-ISCC-Principles-2-6.pdf"
RA_FARMING_ANNEX = "https://knowledge.rainforest-alliance.org/docs/es/farming-annex-v14"
LOCAL_BASE_LOAD_DATE = "septiembre de 2026"

WHO_EN = "https://www.who.int/publications/i/item/9789240005662"
WHO_ES = "https://www.who.int/es/publications/i/item/9789240005662"
WHO_PDF = "https://iris.who.int/server/api/core/bitstreams/36c193cd-2362-46d1-be00-fef570d80037/content"
MONTREAL_PROTOCOL = "https://ozone.unep.org/treaties/montreal-protocol"
ROTTERDAM_ANNEX_III = "https://www.pic.int/theconvention/chemicals/annexiiichemicals"
ROTTERDAM_PIC = "https://www.pic.int/en-us/procedures/picprocedure.aspx"
STOCKHOLM_POP_LIST = "https://chm.pops.int/TheConvention/Thepops/Listingofpops/tabid/2509/Default.aspx"
STOCKHOLM_ANNEX_A = "https://chm.pops.int/Implementation/Alternatives/AlternativestoPOPs/ChemicalslistedinAnnexA/tabid/5837/Default.aspx"
STOCKHOLM_ANNEX_B = "https://chm.pops.int/Implementation/Alternatives/AlternativestoPOPs/ChemicalslistedinAnnexB/tabid/5850/Default.aspx"


def reference_blocks_markdown() -> str:
    """Build the informational OMS and convention blocks shown in Streamlit."""
    return f"""**OMS — Clasificación recomendada de plaguicidas por peligrosidad**

La publicación [“The WHO Recommended Classification of Pesticides by Hazard and guidelines to classification, 2019 edition”]({WHO_EN}) fue publicada en 2020 por la OMS y clasifica la peligrosidad aguda para la salud humana en Ia, Ib, II, III y U. No es por sí sola una prohibición legal ni una autorización regulatoria, y es distinta del SGA. ([Versión en español]({WHO_ES}) · [PDF]({WHO_PDF}))

**Protocolo de Montreal — sustancias que agotan la capa de ozono**

El [Protocolo de Montreal]({MONTREAL_PROTOCOL}) controla sustancias que agotan la capa de ozono. En esta aplicación, una referencia a Montreal procede de los criterios documentados en la base local y no se convierte automáticamente en una prohibición RSPO o ISCC.

**Convenio de Rotterdam — Anexo III y procedimiento PIC**

El [Anexo III]({ROTTERDAM_ANNEX_III}) identifica sustancias sujetas al procedimiento de consentimiento fundamentado previo (PIC) en el comercio internacional; esto no equivale a una prohibición universal. [Descripción oficial del procedimiento PIC]({ROTTERDAM_PIC}).

**Convenio de Estocolmo — contaminantes orgánicos persistentes (POP)**

El [listado oficial de POP]({STOCKHOLM_POP_LIST}) incluye sustancias de los anexos A, B y C; las obligaciones dependen del anexo aplicable. Consulta también los listados de [Anexo A]({STOCKHOLM_ANNEX_A}) y [Anexo B]({STOCKHOLM_ANNEX_B})."""


def standards_scope_markdown() -> str:
    """Build the RSPO, ISCC and RA scope block shown in Streamlit."""
    return f"""**RSPO — marco principal:** [Principios y Criterios RSPO 2024, versión 4.2]({RSPO_PNC_2024_ES}), indicador 7.1.2 (C). La aplicación mapea como criterios explícitos: OMS Ia/Ib (también expresado como 1A/1B en el documento); carcinogenicidad, mutagenicidad o toxicidad reproductiva SGA 1A/1B; Convenios de Estocolmo o Rotterdam; y Paraquat. Las restricciones nacionales requieren verificación aparte.

**ISCC — marco principal:** [ISCC EU 202-2 v1.1]({ISCC_EU_202_2}) (válido desde el 1 de diciembre de 2022), requisito 2.4.1. La aplicación mapea los criterios explícitos verificados: OMS Ia/Ib, Convenio de Estocolmo y Anexo III del Convenio de Rotterdam. No amplía automáticamente ISCC a otros criterios.

**Rainforest Alliance — referencia complementaria y base local de detección:** [Anexo al capítulo Agricultura v1.4 (A-07-SCRL-B-FA)]({RA_FARMING_ANNEX}), listas de plaguicidas **prohibidos**, **obsoletos** y **sujetos a mitigación de riesgos**. **Última carga de la base local: {LOCAL_BASE_LOAD_DATE}.**

Los enlaces de la OMS y los convenios son referencias informativas; la aplicación no consulta sus listados en tiempo real ni importa sustancias desde ellos. Solo aplica a RSPO o ISCC las correspondencias explícitas codificadas para los criterios que ya constan en la base local."""
