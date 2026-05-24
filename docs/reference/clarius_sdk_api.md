# Clarius SDK & API Reference
_Source: API and SDK Programming Guide 077-1854-02, March 2026_

## Overview

Clarius exposes two automation interfaces:
1. **REST API** — HTTPS calls to the Clarius VM, JSON payloads, good for system integration
2. **Python SDK (`clariussdk`)** — Python wrapper over the REST API; recommended for test automation scripts

Both require authentication via Bearer token. The SDK handles token management automatically.

---

## REST API Basics

### Base URL
```
https://<<host ip>>:<<port id>>/clarius/<<endpoint>>
```
- Default API port: **8443** (SSL)
- Default API gateway port: **8080**

### Authentication — Get Access Token
```
POST https://<<host ip>>:<<portid>>/clarius/oauth2/token
```
Returns a Bearer token. Include in all subsequent requests:
```
Authorization: Bearer <access_token>
```

### HTTP Methods Used
- `GET` — retrieve data
- `POST` — create or execute
- `PUT` — update
- `DELETE` — delete

### Common Status Codes
| Code | Meaning |
|---|---|
| 200 | Success |
| 400 | Validation failed |
| 401 | Unauthorized |
| 404 | Endpoint not reachable |
| 500 | Server error — contact admin |

---

## Python SDK Quick Start

### Installation
```
clarius-sdk-<<version>>.exe  (i = install, r = reinstall, u = uninstall)
```
Requires Python 3.13.x.

### Import and Initialize
```python
from clariussdk import clarius

ip = "192.168.1.100"       # IP of Clarius host
client_id = "<<id>>"       # as configured
client_secret = "<<secret>>"
api_port = 8443            # SSL port (check portconfiguration.json if changed)
cert_port = 8080           # API gateway port

api = clarius.Api(ip, client_id, client_secret, api_port, cert_port)
```

Port config file location: `C:\Program Files\Tektronix\Clarius\conf\portconfiguration.json`

---

## SDK Workflow: End-to-End Test

### Step 1: Get Licensed Applications
```python
apps = api.applications.get_list()
# Returns: [{name, description, id, category_type, category_subtype, execution_mode}, ...]
```

### Step 2: Create Test Bench (LIVE acquisition)
```python
test_bench = {
    "name": "MyBench",
    "description": "",
    "acquisitionMode": "LIVE",
    "technologies": ["LPDDR4"],           # technology name from the application
    "applications": ["app_id"],
    "hubAddress": "http://<scope_ip>:18000",   # instrument service address
    "instruments": [
        {
            "name": "Scope",
            "type": "SIGNAL_ANALYZER",
            "category": "RT_SCOPE",
            "address": "TCPIP::192.168.1.50::INSTR",   # or GPIB8::1::INSTR
            "description": "",
            "properties": {
                "manufacturer": "TEKTRONIX",
                "model": "default"
            },
            "extensions": []
        }
    ],
    "availability": ""
}
api.test_benches.create_testbench(test_bench)
```

### Step 2 Alt: Create Test Bench (RECORDED waveforms)
```python
test_bench = {
    "name": "MyBench_Recorded",
    "description": "",
    "hubAddress": "http://<pc_ip>:18000",  # instrument service on the PC
    "acquisitionMode": "RECORDED",
    "internal": False
}
api.test_benches.create_testbench(test_bench)
```

### TestBenchValidationOptions (optional)
```python
# Validate before creating:
from clariussdk.testbenches import TestBenchValidationOptions
options = TestBenchValidationOptions(
    perform_validation=True,
    create_on_validation_failure=False   # don't create if validation fails
)
api.test_benches.create_testbench(test_bench, options)
```

### Step 3: Create and Configure a Test
```python
from clariussdk.tests import AcquisitionMode

test_name = "LPDDR4_Compliance_Run1"
test_bench_id = "bench_id_from_step2"
new_test = api.tests.new_test(test_name, test_bench_id, description="")

# Set acquisition mode
new_test.acquisition_mode = AcquisitionMode.LIVE   # or AcquisitionMode.RECORDED

# Add a sequence (technology + application)
new_test.add_sequence("LPDDR4", "LPDDR4 Application Name")

# Get technology object to configure
technology = new_test.get_technology("TEST", "LPDDR4")

# Select the application
technology.applications[0].set_selection(True)
```

### Step 4: Configure Signal Sources
```python
# Get supported technologies
techs = new_test.get_available_technologies()

# Get signal source info
tech = new_test.get_technology("TEST", "LPDDR4")
sources = tech.applications[0].get_signal_sources()
```

Signal source JSON structure:
```json
{
  "name": "",
  "type": "",
  "signals": [
    {
      "name": "",
      "category": "TRANSMITTER | RECEIVER",
      "probeMethod": "SINGLE_ENDED | DIFFERENTIAL",
      "singleEnded": [],
      "differential": []
    }
  ],
  "selected": "true | false"
}
```

### Step 5: Configure Settings (Presets, etc.)
```python
# Example: set preset data (application-specific structure)
update_preset_data = [
    {"table": "TP1", "preset": ["P1"], "lanes": ["Lane5", "Lane6"]},
    {"table": "TP2", "preset": ["P0"], "lanes": ["Lane1"]},
]
technology.applications[0].set_setting("presets", update_preset_data)
```

### Step 6: Configure Measurement Limits (Optional)
```python
# Get all limits
limits = technology.applications[0].get_limits()

# Get a specific limit
limit = technology.applications[0].get_limit("VIHmin", group_name="DC", additional_info={})

# Update limits
limit.update_ideal_value(259.24)
limit.update_low_limit(205.32, ">")      # comparator: ==, !=, >=, >
limit.update_high_limit(309.08, "<")    # comparator: <=, <
```

Limit JSON structure:
```json
{
  "name": "",
  "displayName": "",
  "group": "",
  "idealValue": "",
  "lowLimit": {"value": "", "comparator": ">="},
  "highLimit": {"value": "", "comparator": "<="},
  "unit": "V",
  "additionalInfo": {"DataRate": "<= 1"}
}
```

### Step 7: Run the Test
```python
execution_id = api.tests.start_test(new_test)
print(f"Execution ID: {execution_id}")
```

### Step 8: Monitor Status
```python
# Summary status
test = api.tests.get_status(execution_id)
# Returns: {id, test_name, start_time, end_time, duration, executed_scenarios, status}

# Detailed status
test = api.tests.get_status(execution_id, raw=True)
# Returns full JSON with per-scenario, per-step breakdown
```

Status values: `PASSED`, `FAILED`, `RUNNING`, `ABORTED`

### Step 9: Wait for Completion
```python
api.tests.wait_for_completion(execution_id)
```

### Step 10: Generate Report
```python
# Get available templates
templates = api.templates.get_report_templates()

# Customize report content (optional)
api.reports.customize_report_generation(
    include_plots=True,
    include_waveforms=True,
    include_testbench=True,
    include_test_configuration=True,
    user_comment="LPDDR4 compliance run for DUT rev B",
    logo_path="C:/path/to/logo.png"
)

# Generate
api.reports.generate_report(
    execution_id,
    template_id=templates[0],
    report_name="LPDDR4_Report",
    report_path="C:/reports/"
)
```

### Step 11: Download Waveforms (Optional)
```python
sdk.results.download_waveforms(execution_id, wfm_path="C:/waveforms/")
```

---

## Interrupt / Notification Handling

During a test, Clarius may pause and send an interrupt notification (e.g., probe reconnect, user action needed).

```python
from clariussdk.notifications import InterruptActions

interrupt_notification = api.notifications.pull_interrupt_notifications()

for notification in interrupt_notification:
    if "executionId" in notification and notification["executionId"] == execution_id:
        # Options: RESUME, SKIP, STOP, CLEAR
        api.notifications.perform_interrupt_action(
            notification["notificationId"],
            InterruptActions.RESUME
        )
        break
```

---

## Sequences (Saved Test Configurations)

```python
# Create and save a sequence
sequence = api.sequences.new_sequence("LPDDR4_Daily_Run", "Standard compliance sequence")
id = api.sequences.save_sequence(sequence)

# Run a saved sequence
imported = api.sequences.import_sequence("sequence_id")
imported.test_name = "LPDDR4_Run_001"
imported.testbench_id = "bench_id"
execution_id = api.tests.start_test(imported)

# Get all sequences
sequences = api.sequences.get_all_sequences()
# Returns: [{id, name, description}, ...]

# Delete a sequence
api.sequences.delete_sequence("sequence_id")
```

---

## Test Management

```python
# Get all test executions
tests = api.tests.get_all_executions()

# Get filtered list
tests = api.tests.get_filtered_executions(filter_params)

# Abort a running test
api.tests.abort_test(execution_id)

# Delete a test
api.tests.delete_test(execution_id)

# Delete multiple tests
api.tests.delete_tests(["id1", "id2", "id3"])

# Delete waveforms only
api.results.delete_waveforms(["id1", "id2"])
```

---

## Test Bench Management API Reference

```python
# Get all test benches
benches = api.test_benches.get_all_testbenches()

# Get specific bench
bench = api.test_benches.get_testbench(testbench_id)

# Update bench
api.test_benches.update_testbench(testbench_id, updated_bench_json)

# Delete bench
api.test_benches.delete_testbench(testbench_id)

# Validate bench (NEW in v4.0.0)
api.test_benches.validate_testbench(testbench_json)
api.test_benches.validate_testbench_by_id(testbench_id)
api.test_benches.get_validation_status(validation_id)
api.test_benches.abort_validation(validation_id)
api.test_benches.remove_validation(validation_id)
```

---

## REST API Key Endpoints Reference

| Operation | Method | Endpoint |
|---|---|---|
| Get token | POST | `/clarius/oauth2/token` |
| Get licensed apps | GET | `/clarius/application` |
| Get app by ID | GET | `/clarius/application/{id}` |
| Get limits | GET | `/clarius/limits` |
| Get limit by ID | GET | `/clarius/limits/{id}` |
| Update limit | PUT | `/clarius/limits/{id}` |
| Create test bench | POST | `/clarius/testbench` |
| Get test benches | GET | `/clarius/testbench` |
| Update test bench | PUT | `/clarius/testbench/{id}` |
| Delete test bench | DELETE | `/clarius/testbench/{id}` |
| Validate test bench | POST | `/clarius/execution/testbench/validation/$start` |
| Run test | POST | `/clarius/application/$execute` |
| Get test status | GET | `/clarius/application/$execute/{id}` |
| Delete test | DELETE | `/clarius/application/$execute/{id}` |
| Generate report | POST | `/clarius/reports` |
| Get test events | GET | `/clarius/events` |

---

## Test Execution JSON Structure (Key Fields)

```json
{
  "executionName": "My Test",
  "acquisitionMode": "LIVE | RECORDED",
  "waveformFolderPath": "C:/waveforms/",
  "testBenchId": "bench_id",
  "applicationRequests": [
    {
      "technology": "LPDDR4",
      "testCategory": {"type": "TX", "subType": "TEST"},
      "testMode": "Compliance | User-Defined",
      "applicationId": "app_id",
      "loop": {
        "sources": [
          [
            {
              "name": "Source1",
              "signals": [
                {
                  "name": "DQ",
                  "category": "TRANSMITTER",
                  "probeMethod": "DIFFERENTIAL",
                  "differential": ["CH1", "CH2"]
                }
              ],
              "selected": true
            }
          ]
        ]
      },
      "settings": []
    }
  ],
  "generateReport": true,
  "templateId": "template_id"
}
```
**Bold/mandatory fields:** `executionName`, `acquisitionMode`, `testBenchId`, `applicationRequests[].technology`, `applicationRequests[].applicationId`

---

## SDK API v4.0.0 New Functions

- `validate_testbench()` — validate before creating
- `validate_testbench_by_id()` — validate existing bench
- `get_validation_status()` — poll validation progress
- `abort_validation()` — stop validation
- `remove_validation()` — clear validation from memory after completion
- `executionMode` parameter added to application and test execution calls
- `testMode` parameter: `null | "Compliance" | "User-Defined"`

---

## Complete Minimal Example Script

```python
from clariussdk import clarius
from clariussdk.tests import AcquisitionMode

try:
    ip = "192.168.1.100"
    client_id = "admin"
    client_secret = "your_password"
    
    sdk = clarius.Api(ip, client_id, client_secret)
    
    # Create test bench
    test_bench = {
        "name": "LPDDR4_Bench",
        "technologies": ["LPDDR4"],
        "hubAddress": "http://192.168.1.50:18000",  # scope IS address
        "acquisitionMode": "LIVE",
        "instruments": [{
            "name": "MSO58",
            "type": "SIGNAL_ANALYZER",
            "category": "RT_SCOPE",
            "address": "TCPIP::192.168.1.50::INSTR",
            "properties": {"manufacturer": "TEKTRONIX", "model": "default"},
            "extensions": []
        }],
        "availability": ""
    }
    sdk.test_benches.create_testbench(test_bench)
    
    # Create test
    new_test = sdk.tests.new_test("LPDDR4_Run1", "LPDDR4_Bench", "")
    new_test.acquisition_mode = AcquisitionMode.LIVE
    new_test.add_sequence("LPDDR4", "LPDDR4_AppName")
    
    technology = new_test.get_technology("TEST", "LPDDR4")
    technology.applications[0].set_selection(True)
    
    # Run
    execution_id = sdk.tests.start_test(new_test)
    print(f"Test started: {execution_id}")
    
    # Wait and get results
    sdk.tests.wait_for_completion(execution_id)
    result = sdk.tests.get_status(execution_id)
    print(f"Status: {result['status']}")
    
    # Report
    templates = sdk.templates.get_report_templates()
    sdk.reports.generate_report(execution_id, templates[0], "LPDDR4_Report", "C:/reports/")

except Exception as e:
    print(e)
```
