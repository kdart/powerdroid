
TARGETS=INSTALL.html

DOCROOT=/var/www/htdocs
RST2HTML=/usr/bin/rst2html.py
STYLESHEET=/media/css/documents.css

all: $(TARGETS)

install: install-docs

install-docs: $(TARGETS)
	@sudo mkdir -p $(DOCROOT)/doc
	@sudo sh -c 'for F in $?; do cp $$F $(DOCROOT)/doc ; done'
	
clean:
	@for F in $(TARGETS); do rm -f $$F ; done


%.html: %.txt
	$(RST2HTML) --strip-comments --initial-header-level=2 \
	--link-stylesheet --stylesheet=$(STYLESHEET) $*.txt $*.html

