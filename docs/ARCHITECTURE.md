# Architecture

`aoa-xda-connector` is a source-specific adapter that implements a portable
connector-family runtime contract.

## Pipeline

```text
public-safe fixture or bounded public thread snapshot
-> XDA parser
-> normalized topic/post records
-> keyword index
-> claim graph
-> evidence packet
-> answer packet
```

## Portable Layer

The following concepts are connector-family concepts:

- `claim`
- `claim_relation`
- `conflict_report`
- `freshness_report`
- `applicability_report`
- `warning_report`
- answer packet evidence chain
- `read_only=true`
- `network_touched=false`
- `insufficient_evidence`

## XDA-Specific Layer

The following concepts are source/profile-specific:

- XDA HTML parsing
- XDA route policy
- thread URL parsing
- quote/signature stripping
- Android device extraction heuristics
- Pixel 8 Pro / husky starter profile
- fixture shape and seed choices

## No Premature Shared Repo

The portable doctrine is duplicated locally in connector repos for now. A
future shared `aoa-connectors` or connector-family doctrine repo should be
created only after several connectors prove which parts are truly common.
