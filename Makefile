lint:
	ruff check .
	black .


format:
	black .


test:
	pytest