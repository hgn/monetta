# Monetta - Linux Monitoring Daemon

A Logging and System Monitoring Web Server

## Goals and Paradigms

- Targeted for Embedded Environments
- Shift computational tasks to the client (web browser), the server provide raw values
- Stick with Systemd and Journalctl
- Reduce external dependencies - just standard Python, aiohttp and python3-systemd
- If no client is connected the service should idle 100%

# Installation

Debian based distribution:

```
aptitude install python3-systemd
```
