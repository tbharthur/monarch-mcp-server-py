# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) server that integrates with Monarch Money personal finance platform. It provides API access to financial accounts, transactions, budgets, and analytics through the MonarchMoney Python library.

## Development Commands

### Installation & Setup
```bash
# Install dependencies
pip install -r requirements.txt
pip install -e .

# Install development dependencies
pip install -e ".[dev]"

# Run authentication setup (required for first-time use)
python login_setup.py
```

### Code Quality Tools
```bash
# Format code with Black
black src/

# Sort imports with isort
isort src/

# Type checking with mypy
mypy src/

# Run all pre-commit hooks
pre-commit run --all-files

# Run tests
pytest
```

## Architecture

### Core Components

1. **MCP Server** (`src/monarch_mcp_server/server.py`): Main server implementation using FastMCP framework
   - Handles tool registration and request routing
   - Manages async/sync bridging with ThreadPoolExecutor
   - Session management for persistent authentication

2. **Authentication** (`login_setup.py`): Standalone authentication script
   - Interactive MFA support
   - Session persistence to `.mm/mm_session.pickle`
   - Multiple session file location fallbacks

### Key Design Patterns

- **Session Management**: The server checks multiple locations for saved sessions in priority order:
  1. Environment variable `MONARCH_SESSION_FILE`
  2. Local project paths
  3. User home directory `~/.mm/mm_session.pickle`

- **Async/Sync Bridge**: Uses `run_async()` helper to run async MonarchMoney operations in sync MCP tool handlers

- **Error Handling**: Falls back to environment credentials if no session found, with clear user instructions for authentication

### Available MCP Tools

The server exposes these tools through the MCP protocol:
- `setup_authentication`: Get authentication setup instructions
- `check_auth_status`: Check current authentication status
- `get_accounts`: Retrieve all financial accounts
- `get_transactions`: Get transactions with filtering options
- `get_budgets`: Access budget information
- `get_cashflow`: Analyze income/expense cashflow
- `get_account_holdings`: View investment holdings
- `create_transaction`: Create new transactions
- `update_transaction`: Modify existing transactions
- `refresh_accounts`: Request real-time account updates

## Dependencies

- **monarchmoney**: Unofficial Python API client for Monarch Money
- **mcp[cli]**: Model Context Protocol implementation
- **pydantic**: Data validation and settings management
- **python-dotenv**: Environment variable management

## Testing Approach

Tests are configured to use pytest with async support. Test files should be placed in a `tests/` directory following the naming convention `test_*.py`.