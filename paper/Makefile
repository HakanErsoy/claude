# Build the manuscript and its supplement: figures from results/*.json, then the PDFs.
#   make          figures + main.pdf + supplement.pdf
#   make figs     figures only
#   make clean    remove LaTeX by-products (keeps the PDFs and figs/)
# The supplement cross-references the main paper (package xr), so main.pdf is built first.

FIGS := figs/fig_definition.pdf figs/fig_rule.pdf figs/fig_maps.pdf \
        figs/fig_types.pdf figs/fig_wordlength.pdf figs/fig_mbm.pdf \
        figs/fig_pareto.pdf figs/fig_tracking.pdf figs/fig_crb.pdf \
        figs/fig_battery.pdf

all: main.pdf supplement.pdf

figs: $(FIGS)

$(FIGS): make_figures.py $(wildcard ../results/*.json)
	python3 make_figures.py

main.pdf: main.tex refs.bib $(FIGS)
	latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

supplement.pdf: supplement.tex refs.bib main.pdf
	latexmk -pdf -interaction=nonstopmode -halt-on-error supplement.tex

clean:
	latexmk -c main.tex supplement.tex

.PHONY: all figs clean
