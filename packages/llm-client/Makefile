.PHONY: help install install-dev install-all clean build test lint format verify publish

help:
	@echo "Available commands:"
	@echo "  make install          - Install package with default (litellm) dependencies"
	@echo "  make install-dev      - Install package with development dependencies"
	@echo "  make install-all      - Install package with all provider dependencies"
	@echo "  make clean            - Remove build artifacts and caches"
	@echo "  make build            - Build distribution packages"
	@echo "  make test             - Run tests"

install:
	pip install -e .[litellm]

install-dev:
	pip install -e .[dev,litellm]

install-all:
	pip install -e .[all,dev]

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

build: clean
	python -m build

test:
	pytest

# Install specific providers
install-openai:
	pip install -e .[openai]

install-watsonx:
	pip install -e .[watsonx]

install-rits:
	pip install -e .[rits]

install-ollama:
	pip install -e .[ollama]
