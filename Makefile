.PHONY: check test

check:
	/bin/bash -n deep-sleep

test: check
	python3 -m unittest discover -s tests -v
