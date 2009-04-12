
# Built targets from RST files.
TARGETS=INSTALL.html 

DOCROOT=/var/www/powerdroid

RST2HTML=/usr/bin/rst2html.py

# The stylesheet link that will be placed within the built html docs.
STYLESHEET=/media/css/documents.css

all: $(TARGETS)

install: install-docs

install-docs: $(TARGETS)
	@sudo mkdir -p $(DOCROOT)
	@sudo sh -c 'for F in $?; do cp $$F $(DOCROOT) ; done'

clean:
	@for F in $(TARGETS); do rm -f $$F ; done


%.html: %.txt
	$(RST2HTML) --strip-comments --initial-header-level=2 \
	--link-stylesheet --stylesheet=$(STYLESHEET) $*.txt $*.html

