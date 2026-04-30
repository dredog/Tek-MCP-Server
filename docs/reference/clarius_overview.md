# Clarius Automation Framework — Overview & Architecture
_Source: Getting Started Guide 077-1852-02, March 2026_

## What Is Clarius?

Clarius is Tektronix's next-generation compliance test platform — essentially TekExpress rebuilt from the ground up. It runs as a **web application** accessed via browser (Chrome or Edge), not a thick Windows GUI. The measurement engine runs inside a **Hyper-V virtual machine** on the host PC, which isolates the compliance software from the OS and enables clean Docker-based service management.

**Key differentiators vs. TekExpress:**
- Browser-based UI (HTTPS, port 4200 by default)
- Python SDK for automation (not just MATLAB/scripting)
- REST API for remote control
- Runs on the oscilloscope OR on a separate laptop
- Supports pre-recorded waveform analysis (no live scope required)
- Modern dark-mode UI, cloud-ready architecture

---

## Architecture: Two Services

| Service | Where It Runs | What It Does |
|---|---|---|
| **Clarius Measurement Service** | Host PC (inside Hyper-V VM) | Runs compliance algorithms, measurement engine |
| **Clarius Instrument Service** | PC or oscilloscope | Acquires waveforms, sends them to measurement service |

The two can be on the same machine (single-system) or different machines (peer-to-peer or networked). The instrument service communicates on port **18000**.

---

## Deployment Models

### Model 1: Single System
- Laptop/PC runs both Clarius Automation Framework AND Clarius Instrument Service
- Waveforms are pre-recorded files on the same machine
- Accessed via `https://127.0.0.1:4200`

### Model 2: Peer-to-Peer
- Laptop/PC runs Clarius Automation Framework
- Oscilloscope runs Clarius Instrument Service
- Connected via direct Ethernet (1G RJ45)
- Best for live acquisition compliance testing at a bench

### Model 3: Network (Switch/Router)
- Same as Model 2 but through a switch — supports multiple oscilloscopes
- All devices on a private lab network
- Enables one PC to serve multiple test benches

---

## System Requirements

| Requirement | Value |
|---|---|
| OS | Windows 10 Enterprise/Pro (21H1+) or Windows 11 Enterprise/Pro (21H2+) |
| Language | English (United States) only |
| Network | 1 Gbps |
| Browser | Microsoft Edge (default) or Chrome |
| Python (for SDK) | 3.13.x |
| Min RAM | 16 GB system (8 GB allocated to VM minimum) |
| Min Disk | 20 GB (up to 90% of available) |
| Min CPU | 2 logical cores (up to 75% of total) |
| Virtualization | Hyper-V must be enabled; BIOS virtualization must be on |

**RAM Allocation Logic:**
- VM gets: `max(min(50% of total RAM, 16 GB), 8 GB)` by default
- Example: 64 GB system → 32 GB max allocatable → 16 GB default → user can set 16–32 GB

**Disk Allocation Logic:**
- Max = 90% of available disk space
- Min = 20 GB

---

## Port Map

| Service | Default Port | Range |
|---|---|---|
| Clarius UI | 4200 | 4200–4209 |
| Event communication (instruments) | 5672 | 5672–5679 |
| Programming interface (API gateway) | 8080 | 8080–8089 |
| SSL certificates download | 8443 | 8443–8449 |
| Large objects / file store | 9001 | 9001–9009 |
| Instrument service hub | 18000 | fixed |

If a port is taken, installer walks up the range automatically.

---

## Installation Sequence (Fresh Install)

1. Enable BIOS virtualization (contact IT if needed)
2. Set sleep settings to **Never** (Power & Sleep settings)
3. Enable required ports in firewall
4. Enable **Hyper-V** via Control Panel → Programs → Windows Features
5. Download installer from tek.com (Software type, search "Clarius")
6. Run `clarius-automation-framework-<<version>>.exe` as Administrator
7. Accept EULA, choose install path (default: `C:\Program Files\Tektronix\Clarius\`)
8. Set admin password (8+ chars, uppercase + lowercase + number + special char)
9. Configure RAM, Storage, CPU allocation for VM
10. Configure ports (accept defaults unless conflicts exist)
11. Install **Instrument Service** (optional during main install, can do separately)
12. Install **Automation SDK** (Python, optional)
13. Finish — Clarius launches in Edge at `https://127.0.0.1:4200`

**Log on failure:** `C:\ProgramData\Tektronix\Clarius\logs\` (folder is hidden by default)

---

## Instrument Service Installation

**On the same PC (for pre-recorded waveforms):**
- Navigate to: `C:\Program Files\Tektronix\Clarius\installers\instrument\`
- Run `clarius-instrument-service-<<version>>.exe`
- Desktop shortcuts `InstrumentServiceStart.bat` / `InstrumentServiceStop.bat` created on success
- Default install path on oscilloscope: `C:` drive

**On the oscilloscope (for live acquisition):**
- Copy `C:\Program Files\Tektronix\Clarius\installers\instrument\` folder to the scope
- **IMPORTANT:** Copy the folder AFTER installing the compliance application so that app-specific instrument service plug-ins are included
- Run the installer on the scope

**Key note:** Uninstalling instrument service requires reinstalling the app-specific IS plug-in afterward.

---

## SDK Installation

- SDK requires Python 3.13.x
- Installed via `C:\Program Files\Tektronix\Clarius\installers\sdk\clarius-sdk-<<version>>.exe`
- Can install into global Python environment or isolated environment
- Installer is a CLI tool (options: `i` install, `r` reinstall, `u` uninstall)

---

## Upgrade Notes

- v4.0.0 can upgrade from v3.0.0 or v3.1.0
- Need **30 GB free VM disk space** before upgrading
- Do NOT restart/shut down PC during upgrade — no rollback
- Application upgrades DO have rollback to previous version on failure
- Check VM disk space in Admin Console before upgrading
- Expand VM storage via CLI: `clarius --systemInfo manage --storage <GB>`

---

## Application and License Flow

1. Install Clarius Automation Framework (framework only — no apps by default)
2. Install the compliance application (e.g., LPDDR4 app) from tek.com
3. Log into Clarius → License tab → copy **Host ID**
4. Send Host ID to Tektronix AE to get license file
5. License tab → **Add License** → browse to file → **Activate**
6. After activation, application appears on home screen

---

## UI Navigation

| Tab | Purpose |
|---|---|
| Dashboard | Status overview — running tests, sequences, test benches, notifications |
| Tests | Create, configure, run, and review tests |
| Manage | Manage applications, test benches, sequences |
| License | Add/view licenses, copy Host ID |
| Reports | Generate/export test reports |
| Events | View event logs for executed tests |
| Help | Open application help |

---

## Admin Console

- Launch from desktop shortcut: **Clarius Admin Console**
- Shows Host and Clarius Platform (VM) metrics: CPU, Memory, Storage
- Contains: Measurement Service, Clarius Core service status
- Can Restart/Stop/Start services
- **Warning threshold:** 70% (Memory, Storage, CPU) → yellow icon
- **Critical threshold:** 90% → red icon
- Also shows: TLS certificate status, Port configuration, Network connectivity troubleshooting

**TLS Certificate renewal:**
```
clarius --sslCert -r
```
Stop all tests first. Clear browser cache after renewal.

---

## Common CLI Commands (Run as Administrator)

| Task | Command |
|---|---|
| View system info | `clarius --systemInfo view` or `clarius -y view` |
| Expand storage | `clarius --systemInfo manage --storage 125` |
| Expand RAM | `clarius --systemInfo manage --memory 12` |
| Expand CPU | `clarius --systemInfo manage --core 4` |
| Reset admin password | `clarius --resetPwd -p "newpassword"` |
| Renew TLS cert | `clarius --sslCert -r` |
| Restart all services | `clarius restart` |
| Restart one service | `clarius restart "service name"` |
| Reset Hyper-V network | `clarius --resetNetSwitch` |

---

## Troubleshooting Checklist

- System meets min requirements?
- Hyper-V and BIOS virtualization enabled?
- Anti-virus blocking installation?
- Ports available: 9001 / 5672 / 8080 / 4200 / 8443 / 18000 / 18002 / 5060?
- PC and oscilloscope on same LAN segment?
- Port 18000 available for instrument service?
- VM got an IP address? (Check Hyper-V Manager)
- "Waiting for IP address" error → kill task, then: `Get-HNSNetwork | ? Name -Like "Default Switch" | Remove-HNSNetwork` then `restart-computer`
- Login not working? → Check cookies enabled in browser
- Instrument service "Occupied" but no test running? → Restart IS, contact FAE if unresolved

---

## Service Start/Stop

**Measurement Service:** Managed from Admin Console UI (Restart button)

**Instrument Service:**
- Start: Double-click `InstrumentServiceStart.bat` on desktop
- OR navigate to: `C:\Program Files\Tektronix\Clarius\lib\instrument\service\` and run the .bat
- Status: Look for IS icon in Windows system tray (hidden icons)

---

## Test Bench Statuses

| Status | Meaning |
|---|---|
| Available | IS and IS Agent running, no test active |
| Occupied | Test currently running on this bench |
| Unavailable | IS down, IS Agent running — use Start to recover |
| Not Reachable | Both IS and IS Agent unreachable |
