TEX=pdflatex
BIB=bibtex

.PHONY: all clean view

all: main.pdf

main.pdf: main.tex $(wildcard sections/*.tex) references.bib IEEEtran.cls IEEEtran.bst
	@if command -v latexmk >/dev/null 2>&1; then \
		latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex; \
	else \
		$(TEX) -interaction=nonstopmode -halt-on-error main.tex >/dev/null; \
		$(BIB) main >/dev/null; \
		$(TEX) -interaction=nonstopmode -halt-on-error main.tex >/dev/null; \
		$(TEX) -interaction=nonstopmode -halt-on-error main.tex >/dev/null; \
	fi

view: main.pdf
	@if command -v xdg-open >/dev/null 2>&1; then xdg-open main.pdf; else echo "Open main.pdf"; fi

clean:
	rm -f main.aux main.bbl main.blg main.log main.out main.pdf main.synctex.gz main.fdb_latexmk main.fls
