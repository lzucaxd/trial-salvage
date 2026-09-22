.PHONY: install module1 module1-offline test lint clean
ASSET ?= config/assets/gefitinib.yaml

install:
	pip install -e ".[dev]"

module1:
	python -m trial_salvage.module1.run --config $(ASSET) --outdir outputs/module1

module1-offline:
	python -m trial_salvage.module1.run --config $(ASSET) --outdir outputs/module1 --offline

test:
	pytest -q

lint:
	ruff check src tests

clean:
	rm -rf outputs/module1
