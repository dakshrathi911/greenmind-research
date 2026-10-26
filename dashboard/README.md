# GreenMind AI interactive dashboard

A static, interactive dashboard for the matched-service emissions experiment. It reads the committed scenario summary CSV and provides filters, matched-work coverage, matched emissions-reduction comparisons, FDR-significance counts, a scenario table, and CSV export.

## Publish with GitHub Pages

1. Open the repository's **Settings → Pages**.
2. Under **Build and deployment**, set **Source** to **GitHub Actions**.
3. Open **Actions** and select the **Deploy GreenMind AI dashboard** workflow. If the workflow did not run automatically, use **Run workflow**.
4. When the workflow succeeds, open the published URL at `https://dakshrathi911.github.io/greenmind-research/dashboard/`.

The dashboard and CSV are deployed as a small static site. It does not run Python in the browser and does not launch new simulations; it visualizes the already-generated results. The underlying experiments use synthetic inputs, so the page explicitly labels the findings as simulation results rather than production measurements.

## Run locally

From the repository root, start a local static server:

```powershell
python -m http.server 8000
```

Then open `http://localhost:8000/dashboard/`. Keep the terminal running while you use the page.
