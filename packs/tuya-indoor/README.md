# tuya-indoor

Indoor temperature and humidity from your Tuya / Smart Life sensors, one named room per device. It reads Tuya's cloud
for you; it does not control anything.

**What it adds**
- One local, indoor sensor per device in `TUYA_DEVICES` (`tuya-<device id>`), with the name you give it.
- Metrics `temp` (°C) and `humidity` (%). The values are scaled from the device's own specification, so a status of
  `276` on a tenths-of-a-degree sensor is 27.6 °C; Fahrenheit sensors are converted.
- Nothing else: the existing indoor rules (the heat pack's indoor heat index, for one) pick the sensors up by themselves.

**Set up**
1. A cloud project on platform.tuya.com in the data centre your Smart Life account lives in, with *IoT Core* and
   *Authorization Token Management* authorised, and your app account linked (Devices → Link App Account).
2. In `.env`: `TUYA_ACCESS_ID` and `TUYA_ACCESS_SECRET` (the project's Authorization Key), `TUYA_REGION` (`eu`, `us`, `sg`,
   `in` or `cn`; `TUYA_ENDPOINT` overrides it), and `TUYA_DEVICES=<id>=Warm room,<id>=Aircon room`.
3. Restart the app. `docker compose logs app` says `tuya-indoor: ...` once if something is wrong, with Tuya's own words.

**Limits.** It polls every `TUYA_EVERY_MIN` minutes (10 by default, never under 5) because the free tier limits the
calls a month, and its IoT Core trial has to be renewed on Tuya's site now and then; an expired trial shows as a
"permission deny" or "not subscribed" message. A cloud status has no timestamp, so a sensor that has lost Wi-Fi keeps its
last value until Tuya reports it offline. The Access Secret and any device's local key are credentials and are never logged.

**Tests:** `python3 tests/test_tuya_indoor.py` (offline; a fake Tuya, the signature, scaling, token refresh, and that no
error carries a secret).
