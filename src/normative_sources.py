"""Static official reference links for standards and conventions.

These links are informational only. The application does not fetch them at
runtime or use their contents to make evaluation decisions.
"""

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
