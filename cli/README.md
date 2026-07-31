# HPXPANEL CLI

Control-plane CLI for HPXPANEL — built with Typer + Rich.

## Commands

```bash
# Forge a one-time owner seal (Owner Access on the login page)
hpxpanel cli forge-seal

# Show version
hpxpanel cli version

# Help
hpxpanel cli --help
```

## Owner Access

1. Run `hpxpanel cli forge-seal` on the panel host
2. Copy the **SEAL** from the panel output
3. Open the dashboard login → **Owner access**
4. Paste the seal to create / promote / reset / delete the owner

The seal is valid for **5 minutes** and burns after a single use.

`generate-temp-key` still works as a hidden legacy alias for `forge-seal`.
