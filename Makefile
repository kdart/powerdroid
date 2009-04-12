# helper to make stuff
# vim:ts=4:sw=4:softtabstop=0:smarttab

ARCH=$(shell uname -m)
PYTHONVER=2.5
PYTHON=python$(PYTHONVER)
DOCROOT=/var/www/htdocs
PREFIX=/usr

.PHONY: install install-droid install-testcases install-docs \
 clean clean-docs \
 remove-testcases remove-droid

# Package locations
DROID=$(PREFIX)/lib/$(PYTHON)/site-packages/droid
TESTCASES=$(PREFIX)/lib/$(PYTHON)/site-packages/testcases

build: build-droid build-testcases

build-droid:
	$(PYTHON) setup.py build --build-base build/droid

build-testcases:
	$(PYTHON) setup_testcases.py build --build-base build/testcases

sdist: sdist-droid sdist-testcases

sdist-droid:
	$(PYTHON) setup.py sdist -t MANIFEST.in -m MANIFEST

sdist-testcases:
	$(PYTHON) setup_testcases.py sdist -t MANIFEST_TESTCASES.in -m MANIFEST_TESTCASES

docs:
	@sh -c 'cd doc ; make'

install: install-droid install-testcases install-docs

install-droid: build-droid
	sudo $(PYTHON) setup.py install_lib -O2 --skip-build --build-dir build/droid/lib.linux-$(ARCH)-$(PYTHONVER)
	sudo $(PYTHON) setup.py install_scripts --skip-build --build-dir build/droid/scripts-$(PYTHONVER) --install-dir $(PREFIX)/bin
	sudo $(PYTHON) setup.py install_data

install-testcases: build-testcases
	sudo $(PYTHON) setup_testcases.py install_lib -O2 --skip-build --build-dir build/testcases/lib

install-data:
	sudo $(PYTHON) setup.py install_data

install-docs:
	@sh -c 'cd doc ; make install-docs'

clean: clean-docs
	@sh -c 'cd build/droid ; rm -rf lib scripts-$(PYTHONVER)'
	@sh -c 'cd build/testcases ; rm -rf lib scripts-$(PYTHONVER)'
	rm -f MANIFEST MANIFEST_TESTCASES

clean-docs:
	@sh -c 'cd doc ; make clean'

remove-testcases:
	sudo rm -rf $(TESTCASES)

remove-droid:
	sudo rm -rf $(DROID)

