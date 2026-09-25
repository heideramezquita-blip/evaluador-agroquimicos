# Bases locales de plaguicidas

Este directorio contiene las listas normalizadas que utiliza el evaluador como base local de detección documental.

## Archivos

- `master_restrictions.csv`: **PROHIBIDOS** — 165 registros.
- `obsolete.csv`: **OBSOLETOS** — 24 registros.
- `risk_mitigation.csv`: **MITIGACIÓN DE RIESGOS** — 168 registros.

Los archivos conservan una estructura común:

```text
source_list,action,scope,ingredient,cas,usage,criteria,source_code,source_version,source_date
```

## Origen

Las listas fueron normalizadas a partir de la documentación corporativa de gestión de plaguicidas basada en el Anexo al capítulo Agricultura de Rainforest Alliance.

El campo `criteria` conserva el criterio o riesgo asociado a cada entrada, por ejemplo:

- toxicidad aguda OMS 1A / 1B;
- carcinogenicidad;
- mutagenicidad;
- toxicidad para la reproducción;
- Convenios de Montreal, Rotterdam o Estocolmo;
- efectos graves;
- medidas de mitigación aplicables.

Estos campos también permiten realizar un cruce conservador con criterios explícitos de RSPO e ISCC. La correspondencia entre estándares se implementa en `src/rules.py`; no se asume que toda clasificación de Rainforest Alliance sea automáticamente equivalente en los otros estándares.

## Normalización por CAS

- Los registros con CAS específico se normalizan a una fila consultable por CAS.
- Cuando una entrada de origen contiene varios CAS, puede expandirse conservando ingrediente, uso y criterio.
- Las entradas cuyo CAS de origen es `varios` o no específico se mantienen como grupos.

Los grupos se procesan mediante reglas explícitas en `src/prohibited_database.py`. Una coincidencia textual con un grupo amplio no se convierte automáticamente en una decisión fuerte cuando la pertenencia química no es determinística.

## Papel de estas bases

Estas listas son una **fuente local de detección**, no una reproducción completa de todos los requisitos de RSPO, ISCC o de la legislación colombiana.

Actualmente la aplicación prioriza:

- **RSPO**: OMS 1A/1B, CMR SGA 1A/1B, Estocolmo/Rotterdam y Paraquat, además de advertir que las restricciones nacionales deben verificarse aparte.
- **ISCC**: OMS 1a/1b, Estocolmo y Rotterdam, conforme al mapeo explícito implementado.
- **Rainforest Alliance**: se conserva la clasificación completa de PROHIBIDOS, OBSOLETOS y MITIGACIÓN DE RIESGOS como referencia complementaria.

No se incluyen actualmente listas separadas de organofosforados o carbamatos como fuentes de decisión independientes.

## Criterio de decisión

La mera aparición de una sustancia en un PDF no produce automáticamente una prohibición.

El motor combina:

1. identidad química por CAS o nombre;
2. rol contextual de la sustancia en el documento;
3. lista de origen;
4. correspondencia normativa explícita con RSPO/ISCC.

Las menciones incidentales, negadas, de productos de descomposición o de referencia toxicológica no se convierten en decisiones fuertes. Los PDF sin texto extraíble se envían a revisión documental.

## Actualización

La evaluación es determinística y depende de estas copias locales. Si las fuentes normativas cambian, los CSV y las reglas de correspondencia deben revisarse antes de considerar que la aplicación refleja la nueva versión.
