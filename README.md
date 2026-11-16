# Translation Unit Tests

**AI-generated unit tests for MT/LLM translation engines, and the errors segment-level QE can't see.**

Most localization pipelines translate and quality-check one segment at a time. That works for errors that
live inside a segment, but many real failures live *between* segments: a pronoun whose referent is two
lines up, a list item that has to fit its lead-in, terminology or *tú/usted* that drifts across a document.

This project treats translation engines like software: an LLM writes a **capability test suite**
(test inputs plus assertions about the expected output), the suite is validated, and engines are run
against it like a unit-test suite, with a pass/fail dashboard per capability and JUnit XML for CI. The
same outputs also go through segment-level QE, so you can see exactly which failures QE would have missed.

## Results

Suite: 12 capabilities × 8 AI-generated cases across software/UI, marketing, legal and medical content
(92 cases and 194 assertions kept after validation). Engines: Llama 4 Scout, GPT-5.4 nano, GPT-5.4 mini,
each run **segment by segment** (TMS-style) and **whole-document**, EN→ES.
Full write-up: [`RESULTS.md`](RESULTS.md) · dashboard: [`results/mtunit/report.md`](results/mtunit/report.md).

| case pass rate | scout seg | scout doc | nano seg | nano doc | mini seg | mini doc |
|---|---|---|---|---|---|---|
| segment-local capabilities | 85% | 87% | 95% | 97% | 95% | 92% |
| **cross-segment capabilities** | **63%** | 87% | **65%** | 87% | **79%** | 94% |

1. **Segmentation breaks cross-segment capabilities, and only those.** Paired by engine and case,
   cross-segment tests failed only in segment mode 33× vs only in document mode 4× (p ≈ 1×10⁻⁶);
   segment-local capabilities showed no difference (3 vs 2). Same pattern in all three engines.
2. **Segment-level QE misses most of these failures.** Of 102 failures independently confirmed as real
   errors, MQM-style segment QE (run by a strong LLM) flagged the problem as major/critical in **14%**,
   and mentioned it at any severity in **46%**. List items that don't fit their lead-in: **0 of 17**.
3. **AI-written tests need a second check.** 77% of failures were real errors; the rest were over-specific
   assertions. The pipeline includes an independent adjudication step for this reason.

Example caught by the unit tests, not by segment QE (all segments scored clean):

| # | source | segment-by-segment output |
|---|---|---|
| 1 | To reset your password, you must: | Para restablecer tu contraseña, debes: |
| 2 | open the Settings menu | abrir el menú Configuración |
| 3 | select Security | seleccionar Seguridad |
| 4 | click Reset | **haz clic** en Restablecer ← imperative breaks "debes: …" |

## How it works

```
capabilities.py ─► generate.py: an LLM writes N test cases per capability (inputs + assertions)
                 └► validate: assertions must hold on a careful gold translation (others are dropped)
engines.py ──────► each engine translates every case: segment-by-segment and whole-document
assertions.py ───► deterministic checks (preserve / contains / not_contains) + grounded LLM judgments
transtest/segqe ─► segment-level MQM QE on the same outputs (the baseline)
adjudicate.py ───► an independent model labels every failure: real error? did QE identify it?
run.py ──────────► dashboard (report.md), JUnit XML per engine/mode, qe_misses.md
```

Capabilities tested: negation · numbers & locale formats · placeholders/tags · do-not-translate · logical
scope (segment-local); pronoun/gender agreement · terminology consistency · register consistency ·
implicit subjects/ellipsis · list items inheriting a lead-in · context-dependent word sense · UI-label
references (cross-segment).

## Quickstart

```bash
uv sync
cp .env.example .env            # paste an OpenRouter key (or point at any OpenAI-compatible endpoint)
uv run python -m common.check   # one tiny call per configured model

uv run python -m mtunit.run --per-cap 8      # generate → validate → test engines → report
uv run python -m mtunit.adjudicate           # independent review of every failure
```

Engines are configurable: `--engines openai/gpt-5.4-mini,meta-llama/llama-4-scout` (any OpenRouter model id).
All LLM calls are cached on disk (`.cache/`), so re-runs are free. Approximate cost of the full run: ~$10.

## Also in this repo: `transtest`, document-level QA gates

The earlier, exploratory half of the project: test suites written *per source document* and run against a
delivered translation as a QA gate (numbers, glossary, terminology consistency, LaBSE alignment coverage,
register, grounded meaning assertions, QA probes), plus **mutation testing** to measure how good a suite is.

```bash
uv run python -m transtest calibrate transtest/examples/leaflet/suite.yaml
uv run python -m transtest run transtest/examples/leaflet/suite.yaml transtest/examples/leaflet/target_flawed.es.md
uv run python -m transtest mutate transtest/examples/leaflet/suite.yaml transtest/examples/leaflet/target_good.es.md
uv run python -m transtest generate my_doc.en.md --target-lang es --out my_suite.yaml
uv run pytest
```

## Layout

```
mtunit/      engine unit tests: capabilities, generation + validation, engines, assertions, run, adjudicate
transtest/   document-level QA gates: checks/, runner, CLI, mutation testing, suite generation, segment QE,
             examples/leaflet (fictional leaflet, good + flawed Spanish), experiments/
common/      OpenAI-compatible client with disk cache, embeddings, .env loader
results/     mtunit/ (main results), transtest/ (exploratory)
tests/       unit tests for the deterministic checks
```

## License

MIT
