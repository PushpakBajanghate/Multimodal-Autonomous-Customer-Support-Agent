.PHONY: setup backend frontend test dev

setup:
	python -m pip install -r backend/requirements.txt
	npm --prefix frontend install

backend:
	cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

frontend:
	npm --prefix frontend run dev

test:
	LLM_PROVIDER=mock python -m pytest backend/tests -q

dev:
	$(MAKE) -j2 backend frontend
