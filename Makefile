install:
	pip install -r requirements.txt

generate-test-data:
	python generate_test_docs.py

test:
	pytest

run:
	uvicorn app.main:app --reload
