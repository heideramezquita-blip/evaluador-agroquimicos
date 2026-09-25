from __future__ import annotations
from .text_utils import normalize_text
ACTIVE='ACTIVE'; COMPOSITION='COMPOSITION'; INCIDENTAL='INCIDENTAL'; NEGATED='NEGATED'; DECOMPOSITION='DECOMPOSITION_COMBUSTION'; REFERENCE='REFERENCE_TOXICOLOGY'; UNCERTAIN='UNCERTAIN'

def classify_context(context:str, matched_value:str='')->str:
    n=normalize_text(context)
    if any(x in n for x in ('no contiene','no contiene el','does not contain','libre de ')):
        return NEGATED
    if any(x in n for x in ('productos de descomposicion','producto de descomposicion','productos de descoposicion','producto de descoposicion','descomposicion termica','gases de combustion','productos de combustion','en caso de incendio','gases desprendidos','combustion','incendio')):
        return DECOMPOSITION
    if any(x in n for x in ('limite de exposicion','limites de exposicion','valor limite','valores limite','exposicion ocupacional','informacion toxicologica','toxicologia','referencia bibliografica','bibliografia')):
        return REFERENCE
    if any(x in n for x in ('incompatibilidad','incompatibilidades','no compatible','incompatible','precursor','reaccion de condensacion','condensacion con','condensacion del','obtenidos mediante la condensacion')):
        return INCIDENTAL
    if any(x in n for x in ('ingrediente activo','ingredientes activos','active ingredient')):
        return ACTIVE
    if any(x in n for x in ('composicion garantizada','composicion/informacion sobre los ingredientes','composicion informacion sobre los ingredientes','composicion/informacion sobre los componentes','composicion informacion sobre los componentes')):
        return COMPOSITION
    return UNCERTAIN
