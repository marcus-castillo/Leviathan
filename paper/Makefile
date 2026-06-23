# Build the manuscript PDF. Requires a TeX distribution (texlive / MiKTeX).
#   make        -> build main.pdf
#   make clean  -> remove build artifacts

PAPER = main

$(PAPER).pdf: $(PAPER).tex references.bib
	pdflatex -interaction=nonstopmode $(PAPER).tex
	-bibtex $(PAPER)
	pdflatex -interaction=nonstopmode $(PAPER).tex
	pdflatex -interaction=nonstopmode $(PAPER).tex

.PHONY: clean
clean:
	rm -f $(PAPER).aux $(PAPER).bbl $(PAPER).blg $(PAPER).log $(PAPER).out $(PAPER).pdf
