.PHONY: install module1 module1-offline module2 module2-gefitinib module2-olaparib \
        module2-olaparib-brca1 module2-tofersen module2-bapineuzumab module2-all \
        module4 module4-quick module4-cases compare module3-egfr all cases test lint clean
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

# Worked cases with known outcomes. Each is fully offline: module 4 reads a curated
# handoff, so assets module 1 cannot yet build itself are still runnable.
module4-cases:
	python -m trial_salvage.module4.run --case data/cases/onartuzumab_module4.json \
		--outdir outputs/module4_onartuzumab --n-simulations $(NSIM) \
		--benchmark data/benchmark/rescue_benchmark_v0.csv
	python -m trial_salvage.module4.run --module1 outputs/module1/module1_output.json \
		--case data/cases/gefitinib_module4.json \
		--outdir outputs/module4_gefitinib --n-simulations $(NSIM) \
		--benchmark data/benchmark/rescue_benchmark_v0.csv

# The paired slide: same lever, opposite outcome, plus the benchmark validation.
compare:
	python -m trial_salvage.module4.compare \
		--case data/cases/gefitinib_module4.json \
		--case data/cases/onartuzumab_module4.json \
		--benchmark data/benchmark/rescue_benchmark_v0.csv \
		--outdir outputs/module4_comparison

# Full chain currently implemented: 1 -> 2 -> 4.
# (module 3 writes its own outputs and is run separately.)
all: module1 module2-all module4


# Everything a demo needs, no network at all.
cases: module1-offline module2-all module4 module4-cases compare

test:
	pytest -q

lint:
	ruff check src tests

clean:
	rm -rf outputs/module1 outputs/module2 outputs/module4 outputs/module4_gefitinib \
		outputs/module4_onartuzumab outputs/module4_comparison

module3-egfr:
	python -m trial_salvage.module3.run --gene EGFR --pathway R-HSA-177929 \
	  --cbio-study luad_mskcc_2023_met_organotropism --entrez 1956 \
	  --somatic L858R:7-55191822-T-G T790M:7-55181378-C-T G719S:7-55174014-G-A --outdir outputs/module3
