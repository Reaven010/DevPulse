.PHONY: install test lint run clean

install:
	./install/install.sh

test:
	pytest tests/

lint:
	flake8 src/ daemon/ tools/

run:
	python3 src/main.py

clean:
	rm -rf cache/*.json cache/*.png cache/*.svg __pycache__ .pytest_cache
