PYTHON := backend/.venv/bin/python

.PHONY: python-env python-deps test-python check-python topology simulate train dev

python-env:
	python3 -m venv backend/.venv

python-deps:
	$(PYTHON) -m pip install --upgrade pip setuptools wheel
	$(PYTHON) -m pip install -r backend/requirements.txt

test-python:
	cd backend && .venv/bin/python -m pytest -q

check-python:
	cd backend && .venv/bin/python -m compileall -q src/ia src/simulacion src/config src/common

topology:
	cd backend && PYTHONPATH=src .venv/bin/python src/ia/scripts/dev_cli.py topology

simulate:
	cd backend && PYTHONPATH=src .venv/bin/python src/ia/scripts/dev_cli.py simulate --seconds 300

train:
	cd backend && PYTHONPATH=src .venv/bin/python src/ia/scripts/dev_cli.py train --episodes 10 --seconds 600 --run-id local-dqn

dev:
	npm run dev
