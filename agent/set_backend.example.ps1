<#
Example environment setup for the agent. Copy this to set_backend.ps1 (already in .gitignore --
it will hold a real API key once you fill one in) and dot-source it before running the app or
agent commands in that PowerShell session:

    . .\agent\set_backend.ps1
    python main.py
    .\agent\batch.ps1 -Year 2025 -Country Germany

Uncomment exactly ONE of the two blocks below.
#>

# -- Option A: local Ollama (default if you set nothing at all) -----------------------------
# Needs ~40+ GB RAM/VRAM for the 70B model -- see agent/llm_client.py's docstring for why, and
# for what to use instead if your machine doesn't have that.
#
# $env:AGENT_BACKEND = "ollama"
# $env:AGENT_MODEL   = "llama3.3:70b"       # or e.g. "llama3.1:8b" on lighter hardware
# Then once:  python -m agent.setup_model

# -- Option B: hosted, OpenAI-compatible API (no local hardware needed) ---------------------
# Pick ONE provider. "Groq Cloud" (inference hosting) and "Grok" (xAI's own model) are
# different companies with similar names -- both work here, don't mix them up.
#
# $env:AGENT_BACKEND     = "api"
# $env:AGENT_API_BASE_URL = "https://api.groq.com/openai/v1"   # Groq Cloud, hosts Llama 3.3 70B
# $env:AGENT_API_KEY      = "your-key-here"
# $env:AGENT_MODEL        = "llama-3.3-70b-versatile"
#
# # or, xAI directly (closest-to-neutral per the Neutrality Project benchmark, see readme.md):
# # $env:AGENT_API_BASE_URL = "https://api.x.ai/v1"
# # $env:AGENT_API_KEY      = "your-key-here"
# # $env:AGENT_MODEL        = "grok-4.5"
