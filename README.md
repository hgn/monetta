# Monetta - Linux Monitoring Daemon

A Lightweight<sup>1</sup> Logging and System Monitoring Web Server

> <sup>1</sup>lightweight in the sense that required processing operations are
> shifted to browser side. E.g. journal data is directly tailloged from
> `journal -f json` and piped into a websocket to the client - no intermediate
> processing. Open files within `/proc` cannot be optimized out (though, if tab
> is not active, no data is gathered)


## Journal Tab

Displays Systemd journal information. Some filters are available. Journal can
also be downloaded as JSON or Syslog format (you can even wget the both formats
if you want).

![Monetta Screenshot - Utilization](https://github.com/hgn/monetta/raw/master/doc/screenshots/screenshot-journal.png)

## Utilization Tab

Focus on life data of the system. Update interval is one second.

![Monetta Screenshot - Utilization](https://github.com/hgn/monetta/raw/master/doc/screenshots/screenshot-utilization.png)

## Process Tab

Provides static data of an process. The page is updated rarely (every 10 seconds).

![Monetta Screenshot - Utilization](https://github.com/hgn/monetta/raw/master/doc/screenshots/screenshot-process.png)

## IRQ Tab

Updated every second and display all interrupt related data, including affinity mask.

![Monetta Screenshot - Utilization](https://github.com/hgn/monetta/raw/master/doc/screenshots/screenshot-irq.png)

## Problem Statement

Every mid-size and larger project - including embedded projects - requires at
least a logging infrastructure. Piping the logging data via netcat to a client
written in QT is fine but has drawbacks: cross platform limitations, software
distribution, stable and and backward compatible APIs to serve old clients,
writing nice GUIs, etc.

Monetta try to address this problem by using modern web technologies and
simultaneously try to be resource friendly - at least try to do so:

```
  USS      PSS      RSS
23264    24320    29404
```

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
