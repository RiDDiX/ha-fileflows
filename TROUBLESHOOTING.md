# Troubleshooting

## Turn on debug logging first

```yaml
logger:
  logs:
    custom_components.fileflows: debug
```

Restart Home Assistant, reproduce the problem and check **Settings > System > Logs**. Failed requests are logged with method and path, for example `GET /api/status: not found`.

## Setup errors

### "The endpoint is disabled" (`api_disabled`)

FileFlows answered 404 on the endpoint used to check the token.

- With an API token: the API is not enabled or there is no licence. In FileFlows open **Config > API** and enable it. This needs a FileFlows licence and FileFlows 26.10 or newer.
- With only the Fenrus token: the Fenrus endpoint is off. Turn on **Config > Admin > General > Fenrus Dashboard Endpoint**.

If you have no licence, leave the API token empty and use the Fenrus token. You get counts, storage saved and update status, but no switches and no buttons except Refresh Data.

### "FileFlows rejected the token" (`invalid_auth`)

The token is wrong or was regenerated in FileFlows. Copy it again from **Config > API** (or the Fenrus setting) and paste it without anything around it. Leading and trailing spaces are stripped.

If this happens while the integration is already running, Home Assistant shows a re-authentication prompt for the entry. Enter the new token there; you do not need to remove the integration.

### "Failed to connect to FileFlows" (`cannot_connect`)

- Host is the plain IP or hostname, no `http://` and no path.
- Port matches the FileFlows web UI (default 8585).
- **Use SSL** matches how FileFlows is served. For self-signed certificates turn off **Verify SSL Certificate**.
- Home Assistant can reach the server. If both run in Docker, check that they share a network or use the host IP.
- A reverse proxy in front of FileFlows must pass the `X-Timestamp`, `X-Nonce`, `X-Signature` and `X-Webhook-Token` headers through unchanged.
- If the log mentions `timestamp` or `nonce`, it is a clock problem, see below.

### "Enter an API token, a Fenrus webhook token, or both" (`no_token`)

Both token fields were empty. At least one is required.

## Clock skew

Requests with the API token are signed with the current time. FileFlows rejects them when the clocks of Home Assistant and the FileFlows server are more than 5 minutes apart. The server answers 401 with a reason that mentions `timestamp` or `nonce`. In the setup or reconfigure form this shows as "Failed to connect". On a running entry the update fails, the entities go unavailable and the log shows the server's reason. Home Assistant does not ask you to re-authenticate, because the token itself is fine.

Make sure both machines sync time via NTP. For Docker, check the time inside the FileFlows container, not just on the host. The Fenrus token is not affected.

## Entities are unavailable

Sensors show unavailable, not 0, when there is no value.

- **All entities unavailable**: the server cannot be reached or a poll failed. The log has the reason. The integration retries on every update interval.
- **Only some entities unavailable**:
  - With only the Fenrus token, everything that needs the API token stays unavailable (version, current file, workers, nodes, libraries, flows, plugins, tasks, upcoming/recently finished, system paused). The README marks these with **A**.
  - **Update Available** only comes from the Fenrus endpoint. Add the Fenrus token if you want it.
  - Endpoints that fail with an API error (404, HTML instead of JSON, 5xx) are skipped, and their entities stay unavailable. Debug logging shows `Optional endpoint <name> unavailable: <reason>` for each one.
- **NVIDIA sensors missing**: they are only created when FileFlows reports a GPU when the integration starts. Reload the integration after adding a GPU.
- **A node, library, flow or task entity is unavailable**: it was removed in FileFlows. Delete the entity in Home Assistant if you do not need it any more.

## Check which routes your server offers

Open `http://<host>:8585/api/help` (or `https://...`) in a browser. It lists the API routes of your FileFlows version. If a route from the debug log is missing there, your FileFlows version does not provide it and the matching entity stays unavailable. Updating FileFlows usually fixes this.

## Automations stopped working after the update

`binary_sensor.<...>_system_paused` used to be inverted. It is now on when the system is paused. Check automations and cards that use it.

## Reporting an issue

https://github.com/RiDDiX/ha-fileflows/issues

Include the Home Assistant version, the FileFlows version, which token(s) you use and the debug log. Remove tokens from anything you paste.
