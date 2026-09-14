# Architecture

## Stable core

The stable part of the system is:

- domain models
- canonical `DocumentIR`
- canonical `SemanticDocumentIR`
- pipeline recipe model
- adapter registry
- pipeline executor

Concrete libraries and services sit behind ports.

## Extractor rule

Every extractor must return `DocumentIR`.

It must not create a library-specific downstream representation. This is what
allows:

```text
PDF -> PyMuPDF       -> DocumentIR
PDF -> OpenDataLoader -> DocumentIR
```

without changes to downstream stages.

## Planned semantic ports

The project exposes dedicated ports for:

- `StructureAnalyzer`
- `ReadingOrderAnalyzer`
- `TableAnalyzer`
- `FigureAnalyzer`
- `AltTextGenerator`

The general `SemanticAnalyzer` and `MultimodalModel` remain available for broad
or experimental adapters.
