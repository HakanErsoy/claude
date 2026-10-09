# IEEE TSP version: main text (IEEEtran) and supplement. Figures and references
# are shared with ../paper (graphicspath ../paper/figs, bibliography ../paper/refs).
#   make          figures (via ../paper) + main.pdf + supplement.pdf
#   make clean    remove LaTeX by-products

all: main.pdf supplement.pdf

figs:
	$(MAKE) -C ../paper figs

main.pdf: main.tex ../paper/refs.bib figs
	latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

supplement.pdf: supplement.tex ../paper/refs.bib main.pdf
	latexmk -pdf -interaction=nonstopmode -halt-on-error supplement.tex

clean:
	latexmk -c main.tex supplement.tex

.PHONY: all figs clean
