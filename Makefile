.PHONY: help run build package all

help:
	@echo "Targets:"
	@echo "  make run      # run app with Python via uv"
	@echo "  make build    # build one-file binary (PyInstaller)"
	@echo "  make package  # build .deb package (requires dist binary)"
	@echo "  make all      # build binary then package deb"

run:
	./scripts/run-python.sh

build:
	./scripts/build-binary.sh

package:
	./scripts/package-deb.sh

all: build package
