# IEEE TSP version: main text (IEEEtran) and supplement. The text, figures and references
# are shared with ../paper (body.tex, macros.tex, parts/, supp_body.tex, figs/, refs.bib).
#   make          figures (via ../paper) + main.pdf + supplement.pdf
#   make clean    remove LaTeX by-products

all: main.pdf supplement.pdf

figs:
	$(MAKE) -C ../paper figs

SHARED := ../paper/body.tex ../paper/macros.tex $(wildcard ../paper/parts/*.tex) ../paper/refs.bib

main.pdf: main.tex $(SHARED) figs
	latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

supplement.pdf: supplement.tex ../paper/supp_body.tex $(SHARED) main.pdf
	latexmk -pdf -interaction=nonstopmode -halt-on-error supplement.tex

clean:
	latexmk -c main.tex supplement.tex

.PHONY: all figs clean
