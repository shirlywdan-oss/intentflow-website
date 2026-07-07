# From Beauty to Pet Care: Scaling a Search Engine Across Verticals in 24 Hours

*Published on June 28, 2026*

---

When I first built IntentFlow, it was laser-focused on Southeast Asian beauty brands. The taxonomy was deep: serum types, skin concerns, local slang like "kulit kusam" and "bruntusan." It worked beautifully.

Then a pet food brand asked: "Can this work for us too?"

My first instinct was to say no. Pet care has completely different vocabulary, search patterns, and customer intent. But I decided to treat it as an experiment. The goal: expand to pet care in 24 hours without touching core search code.

---

## The Architecture Decision

The key insight was separating three layers:

1. **Search intent parsing** — language-agnostic
2. **Taxonomy graph** — per-category, swappable
3. **Product catalog** — per-merchant, injected at runtime

Because these layers were already decoupled, adding a new vertical meant only one thing: building a new taxonomy graph.

---

## What Changed in 24 Hours

- Added `pet_category`, `pet_type`, and `health_concern` tags to the data model
- Seeded 15 core pet products: cat food, dog food, supplements, grooming
- Mapped local Indonesian terms like "makanan kucing" and "kucing mencret"
- Updated the demo page with a category switcher

The core search algorithm didn't change. Not a single line.

---

## The Result

Pet care search now resolves local terms with the same accuracy as beauty:

- **"makanan kucing"** → dry cat food, wet food, treats
- **"kucing mencret"** → digestive health products, probiotics
- **"vitamin anjing"** → dog vitamins and senior care

A new vertical, one day, zero core code changes.

---

## Why This Matters for SaaS

Vertical SaaS products often get trapped by their own success. The deeper you go into one niche, the harder it looks to expand.

But if you architect around primitives — intent, taxonomy, catalog — expansion becomes a data problem, not an engineering problem. And data problems are much cheaper to solve.

IntentFlow is no longer just a beauty search engine. It's a search infrastructure layer for vertical D2C brands in Southeast Asia.

---

*Want to see how your category performs? Try the [Free Search Audit](https://intentflowapp.com/audit/).*
