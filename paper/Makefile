# Build the CSSP manuscript: figures from results/*.json, then the PDF.
#   make          figures + PDF
#   make figs     figures only
#   make clean    remove LaTeX by-products (keeps main.pdf and figs/)

FIGS := figs/fig_definition.pdf figs/fig_rule.pdf figs/fig_maps.pdf \
        figs/fig_types.pdf figs/fig_wordlength.pdf figs/fig_mbm.pdf

all: main.pdf

figs: $(FIGS)

$(FIGS): make_figures.py $(wildcard ../results/*.json)
	python3 make_figures.py

main.pdf: main.tex refs.bib $(FIGS)
	latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

clean:
	latexmk -c main.tex

.PHONY: all figs clean
