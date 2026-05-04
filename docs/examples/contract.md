---
title: Contract Review
---

# Contract Review

This example shows how to navigate and extract key terms from a PDF contract.

## Upload and Profile

```python
from adx import ADX

dn = ADX()
doc_id = dn.upload("agreement.pdf")
profile = dn.profile(doc_id)
# document_type: "contract"
```

## Navigate by Section

```python
structure = dn.structure(doc_id)
for section in structure["sections"]:
    indent = "  " * section["depth"]
    print(f"{indent}{section['title']} (page {section['start_page']})")
```

```
1. Definitions (page 1)
2. Term and Termination (page 3)
  2.1 Effective Date (page 3)
  2.2 Termination for Cause (page 4)
3. Governing Law (page 5)
4. Confidentiality (page 6)
```

## Search for Specific Clauses

```python
results = dn.search(doc_id, query="termination")
for hit in results["matches"]:
    print(f"Page {hit['page']}: {hit['snippet']}")
```

## Read Specific Pages

```python
page = dn.get_page(doc_id, page_number=4)
for block in page["text_blocks"]:
    if block["type"] == "paragraph":
        print(block["text"])
```

## Extract Key Terms

```python
extraction = dn.extract(doc_id, schema="contract")
for field in extraction["fields"]:
    print(f"{field['name']}: {field['value']}")
    print(f"  Source: page {field['citation']['page']}")
```

```
parties: Acme Corp; Beta LLC
effective_date: January 1, 2024
expiration_date: December 31, 2025
governing_law: State of Delaware
termination_clause: Either party may terminate with 30 days written notice
```

## Validate

```python
result = dn.validate(doc_id, extraction["id"])
# Checks: required fields, citation presence, confidence thresholds
```
