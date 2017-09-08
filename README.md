# Monetta - Linux Monitoring Daemon

A Logging and System Monitoring Web Server

## Problem Statement

Every project, including embedded project need at least a logging
infrastructure. Piping the logging data via netcat to a client written
in QT is fine but has drawbacks: cross platform limitations, software
distribution, keep the API stable and backward compatible with old clients,
writing nice GUIs, etc.

Monetta try to address this problem by using modern web technologies and
simultaneously try to be resource friendly.

Monetta is released under a liberal licence - use it in your project without
any pain!

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
