PORT := $(or $(shell grep "^APP_PORT=" .env 2>/dev/null | cut -d= -f2),8080)
.PHONY: up update bootstrap down restart logs health stats alerts cells rho backup lint test
up:      ; ./install.sh
update:  ; ./update.sh
bootstrap: ; docker compose exec -T app python -c "import os,main,bootstrap,httpx; print(bootstrap.run(main.db(), httpx.Client(timeout=60), float(os.environ['NODE_LAT']), float(os.environ['NODE_LON'])))"
down:    ; docker compose down
restart: ; docker compose up -d --force-recreate app   # apply .env changes
logs:    ; docker compose logs -f app
health:  ; curl -s localhost:$(PORT)/health | python3 -m json.tool
stats:   ; curl -s localhost:$(PORT)/stats  | python3 -m json.tool
alerts:  ; curl -s localhost:$(PORT)/alerts | python3 -m json.tool
cells:   ; curl -s localhost:$(PORT)/cells  | python3 -m json.tool
rho:     ; curl -s localhost:$(PORT)/rho    | python3 -m json.tool
backup:  ; ./backup.sh
lint:    ; bash -n install install.sh backup.sh update.sh bin/planetai && python3 tools/check_sql.py && python3 tools/check_cli_python.py && (python3 -c 'import sqlglot' 2>/dev/null && python3 tools/check_rules.py || echo '  - rule check skipped (pip install sqlglot)') && python3 -m py_compile app/*.py && python3 -c "import yaml;yaml.safe_load(open('config/rules.yml'));yaml.safe_load(open('docker-compose.yml'))" && echo ok
test:    ; mkdir -p /tmp/stub && echo "class Client: pass" > /tmp/stub/httpx.py && PYTHONPATH=/tmp/stub:app python3 tests/test_sources.py && PYTHONPATH=/tmp/stub:app python3 tests/test_meshtastic.py && PYTHONPATH=/tmp/stub:app python3 tests/test_logic.py && PYTHONPATH=/tmp/stub:app python3 tests/test_packs.py
