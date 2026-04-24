Tektronix MCP Server v1.2.0
===========================
AI-assisted SCPI automation for Claude Desktop
20,000+ verified commands across MSO/DPO/MDO/AFG/AWG/SMU families


INSTALLATION
------------
1. Double-click install.bat
2. Restart Claude Desktop

That's it. No Python, no pip, no Docker required.


WHAT IT DOES
------------
Registers this folder's tektronix_mcp_server.exe with Claude Desktop
so Claude gains access to verified SCPI command lookup, live instrument
control, Tek PTA test framework tools, and more.

Claude Desktop launches the server automatically. You do not need to
start or stop it manually.


OPTIONAL: OPENAI VECTOR STORE
------------------------------
If you have an OpenAI API key and a Tektronix vector store ID,
you can enable semantic search as a third search tier.

1. Open: %APPDATA%\Claude\claude_desktop_config.json
   (paste this path into File Explorer's address bar)
2. Find the "tektronix" entry
3. Fill in OPENAI_API_KEY and TEK_VECTOR_STORE_ID
4. Restart Claude Desktop

The server works fully without these keys — the JSON command databases
are the primary and most reliable source.


IF YOU MOVE THIS FOLDER
-----------------------
Run install.bat again from the new location.
It will update the path in Claude Desktop's config automatically.


TROUBLESHOOTING
---------------
Claude doesn't show Tektronix tools:
  -> Restart Claude Desktop after running install.bat

Instrument won't connect:
  -> Verify the VISA address in your script (TCPIP0::x.x.x.x::inst0::INSTR)
  -> Check the instrument is on the same network
  -> Use tek_instrument_discover in Claude to find available instruments

Server not responding:
  -> Check %APPDATA%\Claude\claude_desktop_config.json
     The "command" path should point to tektronix_mcp_server.exe
     in this folder. If you moved the folder, re-run install.bat.


CONTACT
-------
Questions: contact your Tektronix FAE
