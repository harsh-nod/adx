---
title: Examples
---

# Examples

Real-world document processing workflows using DocuNav.

<div class="landing-grid">
  <article class="card">
    <h3><a href="invoice">Invoice Extraction</a></h3>
    <p>Extract vendor, line items, totals, and tax from PDF invoices. Validate arithmetic and cite every field.</p>
  </article>
  <article class="card">
    <h3><a href="contract">Contract Review</a></h3>
    <p>Pull key terms from contracts: parties, dates, governing law, termination clauses. Navigate by section.</p>
  </article>
  <article class="card">
    <h3><a href="financial-model">Financial Model</a></h3>
    <p>Inspect Excel financial models: trace formulas, read assumptions, verify calculations across sheets.</p>
  </article>
</div>

## Quick Patterns

### Upload and Profile

```python
from docunav import DocuNav

dn = DocuNav()
doc_id = dn.upload("document.pdf")
profile = dn.profile(doc_id)
print(f"Type: {profile['document_type']}, Tables: {profile['table_count']}")
```

### Extract and Validate

```python
extraction = dn.extract(doc_id, schema="invoice")
validation = dn.validate(doc_id, extraction["id"])
errors = [c for c in validation["checks"] if c["severity"] == "error"]
if errors:
    print(f"Found {len(errors)} validation errors")
```

### Search and Drill Down

```python
hits = dn.search(doc_id, query="payment terms")
for hit in hits["matches"]:
    page = dn.get_page(doc_id, hit["page"])
    # process page content
```
