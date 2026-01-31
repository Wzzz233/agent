# ADS Automation Plugin

This plugin enables external Python scripts to control Keysight ADS 2025 through a resident Socket server.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ADS Process                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Main Thread (GUI)                                        │  │
│  │  ┌──────────┐    ┌─────────────────────────────────────┐ │  │
│  │  │  QTimer  │───►│ Command Dispatcher (keysight.ads.de)│ │  │
│  │  │  (50ms)  │    └─────────────────────────────────────┘ │  │
│  │  └──────────┘              ▲                             │  │
│  │                            │ command_queue               │  │
│  ├────────────────────────────┼─────────────────────────────┤  │
│  │  Worker Thread             │                             │  │
│  │  ┌─────────────────────────┴─────────────────────────┐  │  │
│  │  │         Socket Server (localhost:5000)             │  │  │
│  │  └────────────────────────▲──────────────────────────┘  │  │
│  └───────────────────────────┼──────────────────────────────┘  │
└──────────────────────────────┼──────────────────────────────────┘
                               │ TCP/JSON
┌──────────────────────────────┼──────────────────────────────────┐
│  External Python Environment │                                  │
│  ┌───────────────────────────┴───────────────────────────────┐ │
│  │                   ads_client.ADSClient                     │ │
│  │  - create_schematic()  - add_instance()  - add_wire()     │ │
│  │  - save_design()       - run_simulation()                 │ │
│  └───────────────────────────────────────────────────────────┘ │
│  (Can use TensorFlow, NumPy, etc. - completely isolated)       │
└─────────────────────────────────────────────────────────────────┘
```

## Installation

### 1. Copy Plugin to ADS Workspace

Copy the `scripting/` folder to your ADS workspace:

```
<Your_ADS_Workspace>/
├── lib.defs              # Add library reference
├── scripting/            # Copy this folder here
│   ├── boot.ael
│   └── boot.py
└── ...
```

### 2. Configure lib.defs

Add the following line to your workspace's `lib.defs`:

```
DEFINE scripting ./scripting
```

### 3. Restart ADS

When ADS opens the workspace, it will:
1. Load the `scripting` library
2. Execute `boot.ael`
3. Call `boot.start_server()` in Python
4. Start listening on `localhost:5000`

### 4. Verify Server Status

Check the ADS status window for:
```
ADS Automation: Initializing from <path>
ADS Automation Server: QTimer Started.
[SocketListener] Listening on localhost:5000
```

## Usage

### From External Python

```python
from ads_client import ADSClient

client = ADSClient()

# Check connection
print(client.ping())

# Create schematic
client.create_schematic("work", "my_amplifier")

# Add components
client.add_instance("ads_rflib", "R", x=1.0, y=2.0, name="R1", 
                    parameters={"R": "50 Ohm"})
client.add_instance("ads_rflib", "C", x=3.0, y=2.0, name="C1",
                    parameters={"C": "1 pF"})

# Connect with wire
client.add_wire([(1.0, 2.5), (3.0, 2.5)])

# Save
client.save_design()
```

## Supported Commands

| Action | Description |
|--------|-------------|
| `ping` | Check server status |
| `get_workspace_info` | Get workspace path and libraries |
| `create_schematic` | Create new schematic cell |
| `add_instance` | Add component to schematic |
| `add_wire` | Connect points with wire |
| `save_design` | Save current design |
| `run_simulation` | Run circuit simulation |

## Troubleshooting

### "Connection refused"
- ADS is not running or workspace not loaded
- Check if another process is using port 5000

### "Unknown action"
- Command not implemented in `boot.py`
- Check `actions` dictionary in `ADSServer` class

### Server not starting
- Check ADS status window for errors
- Verify `lib.defs` syntax
- Ensure Python path is correct

## License

This plugin is provided for use with Keysight ADS under your existing ADS license terms.
