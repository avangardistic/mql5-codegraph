# Local Dashboard Quickstart

```powershell
python -m pip install -e .
cd web
npm ci
npm run build
cd ..
mql5-codegraph serve --root C:\work\Example-MQL5
```

Open the printed loopback URL. Expected outcome:

1. Analysis progresses from running to ready without freezing navigation.
2. Summary cards show repository counts.
3. Searching `OnTick` focuses event handlers and engine methods.
4. Node selection exposes evidence, incoming/outgoing relationships, context, and impact.
5. Diagnostics can open safe source evidence.
