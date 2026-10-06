# TAK12 growth monitoring

Versioned source for the read-only TAK12 growth collector and watchdog used by the scheduled operator loop.

## Runtime

Secrets remain outside this repository:

- `~/.hermes/secrets/tak12-gsc-service-account.json` (mode `600`)
- `POSTHOG_API_KEY`, `TAK12_USERNAME`, `TAK12_PASSWORD`, and `TAK12_KC_SESSION` in `~/.hermes/.env`

Provision Chromium during installation or maintenance, separately from collection so a transient browser download failure cannot discard GSC/PostHog data:

```bash
./monitoring/provision_browser.sh
```

Run the collector through its dependency-declaring wrapper:

```bash
./monitoring/tak12_monitor.sh
```

Run the silent watchdog with the same declared dependencies:

```bash
uv run --with google-auth --with requests --with playwright \
  python monitoring/tak12_watchdog.py
```

The collector retries referral authentication at most once. Known authentication or browser-refresh failures return a sanitized `referral.status: unavailable` section while preserving independent GSC and PostHog results. Unexpected runtime errors remain fail-fast.

## Tests

```bash
uv run --with google-auth --with requests \
  python -m unittest discover -s monitoring/tests -v
bash -n monitoring/tak12_monitor.sh
```

The scheduled host copy may be installed from a reviewed revision, but credentials and refreshed session values must never be copied into this repository or command output.
