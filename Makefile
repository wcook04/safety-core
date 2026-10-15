.PHONY: check layout
layout:
	python3 skills/repository-organization/scripts/check_layout.py --config docs/maintainers/repository-layout.json
	python3 skills/repository-organization/scripts/test_check_layout.py

check: layout
	python3 scripts/check_repository_structure.py
	node scripts/test_map_model.js
	python3 -m unittest discover -s tests
	python3 doctrine.py check
