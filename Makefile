PORT := $(or $(shell grep "^APP_PORT=" .env 2>/dev/null | cut -d= -f2),8080)
.PHONY: up down restart logs health stats alerts cells rho backup lint
up:      ; ./install.sh
down:    ; docker compose down
restart: ; docker compose up -d --force-recreate app   # apply .env changes
logs:    ; docker compose logs -f app
health:  ; curl -s localhost:$(PORT)/health | python3 -m json.tool
stats:   ; curl -s localhost:$(PORT)/stats  | python3 -m json.tool
alerts:  ; curl -s localhost:$(PORT)/alerts | python3 -m json.tool
cells:   ; curl -s localhost:$(PORT)/cells  | python3 -m json.tool
rho:     ; curl -s localhost:$(PORT)/rho    | python3 -m json.tool
backup:  ; ./backup.sh
lint:    ; bash -n install.sh backup.sh && python3 -m py_compile app/*.py && python3 -c "import yaml;yaml.safe_load(open('config/rules.yml'));yaml.safe_load(open('docker-compose.yml'))" && echo ok
