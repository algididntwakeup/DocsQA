# Future Planning: Feedback-Driven Document QA

## Goal

Make the Technical Document QA system improve safely from reviewer feedback without
automatically retraining a model on every document.

The intended learning loop is:

```text
Document
  -> analyzers and rule engine
  -> findings
  -> reviewer decision
  -> structured feedback
  -> validated rule or dictionary update
  -> regression test
  -> improved analyzer version
```

This approach is safer and more practical for engineering documents than letting a
model learn directly from unvalidated production feedback.

## Important Distinction

`spaCy` is an NLP framework. Installing it does not make the application learn from
documents automatically. It is useful for tasks such as tokenization, entity
recognition, and custom NLP model training, but it requires labeled data, training
code, evaluation, and model versioning.

The current application does not use `spaCy`. The primary improvement path should
therefore start with structured feedback, rules, dictionaries, and regression tests.

## Roadmap

### Milestone 1: Structured Reviewer Feedback

Extend issue curation so that every reviewer decision can preserve the reason behind
the decision.

Recommended fields:

```text
issue_id
document_id
rule_code
category
original_text
system_suggestion
review_decision
review_reason
corrected_text
reviewer_id
created_at
```

Recommended decisions:

- `true_positive`: the finding is correct
- `false_positive`: the finding is incorrect
- `missed_issue`: the system failed to detect a problem
- `suggestion_modified`: the reviewer changed the suggestion
- `not_applicable`: the finding is valid in general but irrelevant here

The UI should make this feedback quick to submit from the existing issue card or
review workflow.

### Milestone 2: Technical Dictionary and Rule Exceptions

Use validated feedback to improve deterministic analyzers.

Useful knowledge-base entries include:

- Approved technical terms
- Ignored spelling patterns
- Grammar exceptions
- Standard-specific terminology
- Section-specific rules
- Document-type-specific rules
- Accepted unit and number formats

Example approved terms:

```text
hydrotest
stress-relieving
PWHT
equipment tag
```

Example rule exception:

```text
rule_code: GRAMMAR_001
exception_pattern: "shall be"
scope: technical_document
approved_by: reviewer
active: true
```

All changes should require validation or approval before becoming active in
production. Do not apply raw reviewer feedback directly as executable rules.

### Milestone 3: Feedback as Regression Tests

Important accepted and rejected findings should become regression cases.

Example false-positive case:

```text
Input:
The pressure shall be verified before hydrotest.

Expected:
No grammar finding for "shall be".
```

Example true-positive case:

```text
Input:
The equipement shall be inspected.

Expected:
A spelling finding for "equipement".
```

Suggested organization:

```text
feedback_cases/
  grammar/
  spelling/
  units/
  references/
  tables/
```

Regression cases should be approved before entering CI. This prevents a new rule
change from reintroducing previously fixed false positives or missed findings.

### Milestone 4: Quality Metrics and Confidence

Measure analyzer quality by category instead of only counting total findings.

Core metrics:

```text
precision = correct findings / all generated findings
recall = correct findings found / all expected findings
false positive rate = incorrect findings / all generated findings
reviewer correction rate = modified findings / all generated findings
```

Track metrics separately for:

- Grammar
- Spelling
- References
- Units
- Table math
- Revision metadata
- Duplicate content
- Ambiguity

Add a confidence or evidence score to findings where practical. A possible policy is:

```text
0.90 and above: primary issue
0.60 to 0.89: review suggestion
below 0.60: retain for analysis, do not show as a strong issue
```

Confidence should consider rule strength, dictionary status, document section,
standard context, and historical reviewer decisions.

### Milestone 5: Active Learning Queue

Prioritize reviewer attention where it has the highest value:

- Low-confidence findings
- Rules with high false-positive rates
- New technical terms
- Patterns not covered by the current dictionary
- Documents that differ significantly from existing examples

This reduces repetitive review work and produces better training data over time.

### Milestone 6: Semantic Search and RAG

After enough reviewed documents exist, add semantic search for precedent and context.

The system can retrieve:

- Similar clauses from approved documents
- Similar historical findings
- Previous reviewer decisions
- Relevant reference-pack material
- Approved wording examples

RAG should support the reviewer and provide traceable sources. It should not replace
deterministic checks for page numbers, calculations, revision metadata, references,
units, and document-control requirements.

A typical flow is:

```text
New clause
  -> retrieve similar approved clauses
  -> show source and prior decision
  -> generate a suggestion
  -> require reviewer confirmation
```

### Milestone 7: Custom NLP Model Only When Justified

Consider `spaCy` or another custom model only after a specific task and dataset have
been established.

Possible engineering-document labels include:

```text
EQUIPMENT_TAG
STANDARD
MATERIAL
PROCESS
UNIT
REVISION
DOCUMENT_NUMBER
```

Example labeled text:

```text
The vessel V-101 shall be inspected according to API 510.

V-101  -> EQUIPMENT_TAG
API 510 -> STANDARD
```

Required before deployment:

1. Collect validated examples.
2. Define labeling rules.
3. Split training and evaluation data.
4. Train the model.
5. Measure precision, recall, and F1.
6. Compare the model against the current rule engine.
7. Version the model and its dataset.
8. Provide rollback if quality decreases.

Do not train directly from raw reviewer feedback. Reviewer decisions must be
validated and consistently labeled first.

## Recommended Implementation Order

```text
1. Structured reviewer feedback
2. Engineering dictionary
3. Rule exceptions
4. Approved regression tests
5. Confidence and quality metrics
6. Active-learning review queue
7. Semantic search/RAG
8. Custom NLP model if the data supports it
```

## Safety Rules

- Never activate raw feedback as a rule without validation.
- Never let one document permanently change production behavior automatically.
- Keep analyzer, dictionary, and model versions traceable in findings.
- Preserve the original text and source location for every learned pattern.
- Keep deterministic safety and document-control checks independent from model output.
- Require regression tests for every rule change that affects issue generation.
- Allow administrators to deactivate incorrect dictionary entries and exceptions.

## Definition of "Getting Smarter"

For the first versions, the system is getting smarter when it can:

```text
find an issue
  -> receive a reviewer correction
  -> remember the validated pattern
  -> avoid repeating the same mistake
  -> prove the improvement with a regression test
```

That feedback-driven behavior provides measurable improvement without the risk and
operational cost of automatic retraining after every uploaded document.
