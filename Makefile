.PHONY: install module1 module1-offline module2 module2-gefitinib module2-olaparib \
        module2-olaparib-brca1 module2-tofersen module2-bapineuzumab module2-all \
        module4 module4-quick all test lint clean
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

# Module 2 needs no network and no GPU: it reads the committed score tables in data/module2.
# Re-scoring from scratch needs a GPU -- see scripts/score_module2_case.py.
module2: module2-gefitinib

module2-gefitinib:
	python -m trial_salvage.module2.run --config config/assets/gefitinib.yaml \
		--offline --outdir outputs/module2/gefitinib

module2-olaparib:
	python -m trial_salvage.module2.run --config config/assets/olaparib.yaml \
		--offline --outdir outputs/module2/olaparib-brca2

module2-olaparib-brca1:
	python -m trial_salvage.module2.run --config config/assets/olaparib.yaml \
		--selection-gene BRCA1 --offline --outdir outputs/module2/olaparib-brca1

module2-tofersen:
	python -m trial_salvage.module2.run --config config/assets/tofersen.yaml \
		--offline --outdir outputs/module2/tofersen

module2-bapineuzumab:
	python -m trial_salvage.module2.run --config config/assets/bapineuzumab.yaml \
		--offline --outdir outputs/module2/bapineuzumab

module2-all: module2-gefitinib module2-olaparib module2-olaparib-brca1 module2-tofersen \
             module2-bapineuzumab

# Full chain currently implemented: 1 -> 4, with 2 runnable offline from committed tables.
all: module1 module2-all module4

test:
	pytest -q

lint:
	ruff check src tests

clean:
	rm -rf outputs/module1 outputs/module2 outputs/module4

module3-egfr:
	python -m trial_salvage.module3.run --gene EGFR --pathway R-HSA-177929 \
	  --cbio-study luad_mskcc_2023_met_organotropism --entrez 1956 \
	  --somatic L858R:7-55191822-T-G T790M:7-55181378-C-T G719S:7-55174014-G-A --outdir outputs/module3
