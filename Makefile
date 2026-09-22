.PHONY: install module1 module1-offline module4 module4-quick all test lint clean
ASSET ?= config/assets/gefitinib.yaml
NSIM ?= 2000

install:
	pip install -e ".[dev]"

module1:
	python -m trial_salvage.module1.run --config $(ASSET) --outdir outputs/module1

module1-offline:
	python -m trial_salvage.module1.run --config $(ASSET) --outdir outputs/module1 --offline

# Module 4 needs no network: it reads module 1's JSON handoff.
module4:
	python -m trial_salvage.module4.run --module1 outputs/module1/module1_output.json \
		--outdir outputs/module4 --n-simulations $(NSIM)

module4-quick:
	python -m trial_salvage.module4.run --module1 outputs/module1/module1_output.json \
		--outdir outputs/module4 --quick

# Full chain currently implemented: 1 -> 4.
all: module1 module4

test:
	pytest -q

lint:
	ruff check src tests

clean:
	rm -rf outputs/module1 outputs/module4

module3-egfr:
	python -m trial_salvage.module3.run --gene EGFR --pathway R-HSA-177929 \
	  --cbio-study luad_mskcc_2023_met_organotropism --entrez 1956 \
	  --somatic L858R:7-55191822-T-G T790M:7-55181378-C-T G719S:7-55174014-G-A --outdir outputs/module3
