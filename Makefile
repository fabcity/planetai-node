PORT := $(or $(shell grep "^APP_PORT=" .env 2>/dev/null | cut -d= -f2),8080)
.PHONY: up update bootstrap down restart logs health stats alerts cells rho backup lint test ship released check-floors
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
# A merge is not a release: install.sh and bin/planetai reach a tester inside the tarball, which only
# changes when somebody rebuilds it. `released` asks whether the site is behind; `ship` fixes it.
# `released` exits 1 when behind, so a script can gate on it — make prints its own error line then.
# Every version floor the installer asserts, with the vendor URL and the date somebody read it.
# Fails when an entry is older than 180 days: a moved floor should be a red build, not a wasted evening.
check-floors: ; @python3 tools/check_floors.py
released: ; @tools/ship.sh --check
ship:    ; tools/ship.sh
# Import the app the way uvicorn does. Catches module-level errors that pass every static check —
# a function called as if it were a string took the node down for an hour (5 Sep). Needs the app's deps installed.
import-check:
	@cd app && DATABASE_URL=postgresql://x:x@127.0.0.1:1/x NODE_NAME=t NODE_CITY=bali NODE_LAT=-8.8 NODE_LON=115.1 PACKS_DIR=../packs \
	  timeout 60 python3 -c "import main; assert len(main.app.routes) > 15; print('  app imports,', len(main.app.routes), 'routes')" > /tmp/planetai-import.log 2>&1; rc=$$?; \
	  grep -vE "bootstrap failed|Is the server|connection to server|Connection refused|GSSAPI|^ *$$" /tmp/planetai-import.log; exit $$rc
lint:    ; bash -n install install.sh backup.sh update.sh bin/planetai tools/preflight.sh tools/ship.sh && python3 tools/check_floors.py && python3 tools/gen_floors.py --check && python3 tools/render_platforms.py --check && python3 tools/extract_strings.py --check && python3 tools/check_sql.py && python3 tools/check_cli_python.py && python3 tools/check_docs.py && python3 tools/check_ui.py && bash tools/check_requirements.sh && (python3 -c 'import sqlglot' 2>/dev/null && python3 tools/check_rules.py || echo '  - rule check skipped (pip install sqlglot)') && python3 -m py_compile app/*.py && (python3 -c 'import pyflakes' 2>/dev/null && python3 -m pyflakes app/*.py packs/*/*.py | grep -v 'imported but unused' | grep . && exit 1 || true) && python3 -c "import yaml;yaml.safe_load(open('config/rules.yml'));yaml.safe_load(open('docker-compose.yml'));[yaml.safe_load(open(w)) for w in __import__('glob').glob('.github/workflows/*.yml')]" && (if python3 -c 'import fastapi' 2>/dev/null; then $(MAKE) -s import-check; else echo '  - import check skipped (pip install -r app/requirements.txt to enable)'; fi) && echo ok
test:    ; bash tests/test_release_consistency.sh && bash tests/test_ship_gate.sh && bash tests/test_daemon_state.sh && bash tests/test_diagnose.sh && bash tests/test_remove.sh && bash tests/test_sudo_prompt.sh && bash tests/test_running_state.sh && bash tests/test_preflight.sh && bash tests/test_geocode.sh && mkdir -p /tmp/stub && echo "class Client: pass" > /tmp/stub/httpx.py && PYTHONPATH=/tmp/stub:app python3 tests/test_sources.py && PYTHONPATH=/tmp/stub:app python3 tests/test_nearby.py && PYTHONPATH=/tmp/stub:app python3 tests/test_forecast.py && PYTHONPATH=/tmp/stub:app python3 tests/test_meshtastic.py && PYTHONPATH=/tmp/stub:app python3 tests/test_logic.py && PYTHONPATH=/tmp/stub:app python3 tests/test_packs.py && PYTHONPATH=/tmp/stub:app python3 tests/test_settings.py && PYTHONPATH=/tmp/stub:app python3 tests/test_report_schedule.py && PYTHONPATH=/tmp/stub:app python3 tests/test_report_templates.py && python3 tests/test_shipped.py && python3 tests/test_check_ui.py && python3 tests/test_dashboard.py && python3 tests/test_ground.py && PYTHONPATH=/tmp/stub:app python3 tests/test_briefing.py && PYTHONPATH=/tmp/stub:app python3 tests/test_earth.py
