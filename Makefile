.PHONY: help test

help:  ## list the tasks
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/' | expand -t 16

test:  ## run every test: the repo's checks, then each plugin's own tests and validation
	python3 -m unittest discover -s tests
