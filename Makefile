.PHONY: check

check:
	zsh -n launch-spore.command
	PYTHONDONTWRITEBYTECODE=1 python3 -W error -m unittest discover -s tests -v
