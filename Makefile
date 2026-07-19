.PHONY: test lint format sast compile ci install-dev live-test

PYTEST = python -m pytest
RUFF = python -m ruff
BANDIT = python -m bandit

# ── Development ────────────────────────────────────────────────────

install-dev:
	pip install -e ".[test]"

# ── Quality ────────────────────────────────────────────────────────

lint:
	$(RUFF) check plugins/ tests/

format:
	$(RUFF) format plugins/ tests/

format-check:
	$(RUFF) format --check plugins/ tests/

sast:
	$(BANDIT) -r plugins/ -ll -q

compile:
	python -m compileall plugins/

# ── Testing ────────────────────────────────────────────────────────

test:
	$(PYTEST) tests/ -q -v

live-test:
	POLZA_API_KEY="$${POLZA_API_KEY:?set POLZA_API_KEY env var}" \
		$(PYTEST) tests/test_polza_live.py -x -v

# ── CI pipeline (same as GitHub Actions) ───────────────────────────

ci: lint sast compile test
	@echo "✅ All checks passed"
