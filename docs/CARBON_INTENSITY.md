# Carbon intensity provider

GreenMind AI supports Electricity Maps as an optional external grid-carbon source.
The backend uses the latest carbon-intensity endpoint and expects intensity in
**gCO2e/kWh**. It converts this to kg CO2e for the dashboard's one-hour energy
reading.

## Configure

1. Obtain an Electricity Maps API token with access to the carbon-intensity signal.
2. Verify the correct zone for the deployment region using the authenticated
   `GET https://api.electricitymaps.com/v5/zones` endpoint.
3. Confirm that the returned zone is commercially available and that its
   `access` list includes `carbon-intensity`.
4. Set these variables in the shell that starts the backend:

   - `ELECTRICITY_MAPS_API_TOKEN`: your private API token
   - `ELECTRICITY_MAPS_ZONE`: the exact verified zone key

Do not commit a real token or put it in frontend code. The optional
`.env.example` contains variable names only; it is not loaded automatically.

### Windows PowerShell example

```powershell
$env:ELECTRICITY_MAPS_API_TOKEN = "YOUR_PRIVATE_TOKEN"
$env:ELECTRICITY_MAPS_ZONE = "YOUR_VERIFIED_ZONE"
python -m uvicorn backend.main:app --reload
```

Restart the backend after changing environment variables.

## Fallback behavior

If either setting is missing, or the provider request fails, the backend uses
the existing fixed factor of **676 gCO2e/kWh (0.676 kg CO2e/kWh)**. The API
response and dashboard label this as a fallback estimate. Provider responses
are cached for 15 minutes to avoid making a network request on every dashboard
refresh.

Check the active configuration at `GET /api/carbon-intensity`. The response
includes the source, mode, zone, provider timestamp, estimation flag, and
fallback reason where applicable.

## India coverage note

Do not guess an India zone identifier. Electricity Maps' authenticated zones
response is token-dependent and reports commercial availability and signal
access. Verify the exact India/state zone returned for the account before
setting `ELECTRICITY_MAPS_ZONE`. Until then, GreenMind correctly remains on
the clearly labelled fallback factor.
