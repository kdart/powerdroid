# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# helper to make stuff
# vim:ts=4:sw=4:softtabstop=0:smarttab

PYTHON=python2.4
DOCROOT=/var/www/htdocs
PREFIX=/usr
CC=gcc-3.3
ARCH=$(shell uname -m)

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

install: install-droid install-testcases

install-droid: build-droid
	sudo $(PYTHON) setup.py install_lib -O2 --skip-build --build-dir build/droid/lib.linux-$(ARCH)-2.4
	sudo $(PYTHON) setup.py install_scripts --skip-build --build-dir build/droid/scripts-2.4 --install-dir /usr/bin
	sudo $(PYTHON) setup.py install_data

install-testcases: build-testcases
	sudo $(PYTHON) setup_testcases.py install_lib -O2 --skip-build --build-dir build/testcases/lib

install-data:
	sudo $(PYTHON) setup.py install_data

install-docs: install-docs-droid install-docs-testcases
	@sh -c 'cd doc ; make install-docs'

install-docs-droid:
	@sh install_docs.sh droid droid

install-docs-testcases:
	@sh install_docs.sh testcases testcases

clean: clean-docs
	@sh -c 'cd build/droid ; rm -rf lib scripts-2.4'
	@sh -c 'cd build/testcases ; rm -rf lib scripts-2.4'
	rm -f MANIFEST MANIFEST_TESTCASES

clean-docs:
	@sh -c 'cd doc ; make clean'

remove-testcases:
	sudo rm -rf $(TESTCASES)

remove-droid:
	sudo rm -rf $(DROID)

