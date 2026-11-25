"""Benchmark protocol. Changing anything here changes what the run produces; it is recorded in the manifest."""

SEED = 20261124

# A different model plants and verifies errors than the models that detect them.
PLANT_MODEL = "gpt-5.5-2026-04-23"
PLANT_EFFORT = "medium"
DETECT_MODELS = ["gpt-5.4-mini-2026-03-17"]   # gpt-5.4 ran in the pilot only (budget)
DETECT_EFFORT = "low"
DIAGNOSIS_MODEL = "gpt-5.4-2026-03-05"   # checks that a detection describes the planted change; not the detector

CORPORA = ["leaflet"]                                 # real documents only (budget)
CANDIDATES_PER_DOC = {"synthetic": 1, "leaflet": 3}   # planting attempts per document and error type
MAX_PER_CELL = 12                                     # verified variants kept per corpus x error type

# False alarms on the long real leaflets are estimated on a fixed random sample of segments (per-segment checks are
# one call per segment, and context QE re-reads the whole document each time). Synthetic documents run in full.
CLEAN_SEGMENTS_PER_LEAFLET = 12

VERIFY_BATCH = 8   # edits verified per round; part of the protocol (it decides which edits get verified)
WORKERS = 16

# Hard spending cap for everything this benchmark has sent to the API (all models, pilot included), computed from
# the token usage recorded in the cache at the list prices below. Calls stop once it is reached.
BUDGET_USD = 39.0
# USD per 1M tokens (input, cached input, output), standard tier, developers.openai.com/api/docs/pricing, 2026-11-24
PRICES = {"gpt-5.4-2026-03-05": (2.50, 0.25, 15.00), "gpt-5.4-mini-2026-03-17": (0.75, 0.075, 4.50),
          "gpt-5.5-2026-04-23": (5.00, 0.50, 30.00)}
