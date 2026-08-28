# Consumer Health Vocabulary references for the patient-language normalisation prototype

## 1. What this resource is

The Consumer Health Vocabulary (CHV/OCHV) line of work maps consumer/patient expressions to canonical biomedical concepts, commonly linked to UMLS Concept Unique Identifiers (CUIs). It is directly relevant to the prototype flow:

patient wording -> candidate consumer/clinical terms -> canonical concept -> patient confirmation -> downstream retrieval

## 2. Real flat-file dataset used for the prototype

A public mirror of the 2011 CHV flat file is available in the GitHub repository:

- Repository: https://github.com/Planeshifter/node-chvocab
- Data directory: https://github.com/Planeshifter/node-chvocab/tree/master/data
- Main flat file: `CHV_concepts_terms_flatfile_20110204.tsv`
- Approximate size: 19.7 MB

The loader in that repository documents these columns:

1. `CUI`
2. `Term`
3. `CHV_preferred_name`
4. `UMLS_preferred_name`
5. `Explanation`
6. `UMLS_preferred`
7. `CHV_preferred`
8. `Disparaged`
9. `Frequency_Score`
10. `Context_Score`
11. `CUI_Score`
12. `Combo_Score`
13. `Combo_Score_NoTopWords`
14. `CHV_String_Id`
15. `CHV_Concept_Id`

The important distinction is that this is not a hand-written list limited to urinary symptoms. It contains a broad consumer-health vocabulary with multiple surface terms mapped to canonical concepts/CUIs.

## 3. Research background

Useful starting papers/resources:

- Zeng QT, Tse T. Exploring and developing consumer health vocabularies. Journal of the American Medical Informatics Association.
- Consumer Health Vocabulary / Open Consumer Health Vocabulary research describing consumer expressions and mappings to UMLS concepts.
- UMLS Metathesaurus documentation from the U.S. National Library of Medicine for the broader concept-normalisation model.

UMLS: https://www.nlm.nih.gov/research/umls/
UMLS Metathesaurus: https://www.nlm.nih.gov/research/umls/knowledge_sources/metathesaurus/

## 4. What we will and will not claim

The public CHV flat file is English-centric and old. It is useful as a real, broad concept/term baseline, but it is not by itself a complete modern Chinese patient-language vocabulary.

Therefore the prototype should separate:

- **real controlled vocabulary layer:** CHV/UMLS concept identifiers and canonical terms;
- **patient-language matching layer:** initially lexical/vector matching, later a multilingual embedding model and/or LLM-assisted candidate generation;
- **patient confirmation layer:** patient selects among Top-K candidates, preventing an unverified model-generated concept from silently becoming a patient fact.

## 5. Current implementation in this repository

Branch: `langgraph-agent-refactor`

- `portal/models.py`: `MedicalConcept`, `MedicalTerm`, `ConceptConfirmation`
- `portal/management/commands/import_chv.py`: imports the complete CHV TSV into SQLite
- `portal/concept_demo.py`: candidate matching logic
- `portal/concept_views.py`: Django API/views
- `templates/portal/concept_demo.html`: patient confirmation UI

Import command after downloading the flat file:

```powershell
python manage.py migrate
python manage.py import_chv C:\path\to\CHV_concepts_terms_flatfile_20110204.tsv --replace
```

This gives us a real broad vocabulary base. The next comparison should evaluate lexical matching, multilingual vector matching, and LLM-assisted candidate generation on the same confirmed patient utterances.
