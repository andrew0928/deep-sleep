.PHONY: check test

check:
	/bin/bash -n deep-sleep
	/bin/sh -n install.sh

test: check
	python3 -m unittest discover -s tests -v
