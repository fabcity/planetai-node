Site presets: coordinates, time zone, language, and the city's open-data portal where it has a CKAN one.
Four are Fab City Index pilots; Delhi is here as a worked example of a site that is not.

    ./install.sh --preset barcelona --name lab-roof --airgradient ag1.local

Everything a preset sets can be overridden by a flag or edited in `.env` afterwards. Nowhere on this list? Run without a preset and pass `--lat --lon`. A node bootstraps from global sources at
any coordinates on earth, so nothing depends on being listed here.

Adding your city is one file and a pull request. Copy the closest one, change the five values, and set
`BAD_ENABLED=0` unless you are in Bali. If your city runs a CKAN portal, add it; test the URL first with
`https://<domain>/api/3/action/package_search?rows=0`.
