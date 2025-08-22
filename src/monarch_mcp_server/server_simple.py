"""Monarch Money MCP Server - Simplified version without threading issues."""

import os
import logging
import json
from typing import Optional
from datetime import datetime

from mcp.server.fastmcp import FastMCP
from monarchmoney import MonarchMoney
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Monarch Money MCP Server")

# Global MonarchMoney instance
_monarch_client: Optional[MonarchMoney] = None


def get_monarch_client_sync() -> MonarchMoney:
    """Get or create MonarchMoney client instance synchronously."""
    global _monarch_client
    
    if _monarch_client is None:
        _monarch_client = MonarchMoney()
        
        # Try to load existing session first - check multiple locations
        session_locations = [
            os.getenv("MONARCH_SESSION_FILE", "monarch_session.json"),
            "/Users/arthur/Dev/monarch-mcp-server-py/monarch_session.json",
            "/Users/arthur/Dev/monarch-mcp-server-py/.mm/mm_session.pickle",
            os.path.expanduser("~/.mm/mm_session.pickle")
        ]
        
        for session_file in session_locations:
            if os.path.exists(session_file):
                logger.info(f"Found session file: {session_file}")
                try:
                    _monarch_client.load_session(session_file)
                    logger.info(f"Successfully loaded Monarch Money session from: {session_file}")
                    return _monarch_client
                except Exception as e:
                    logger.error(f"Failed to load session from {session_file}: {e}")
        
        # If no session found, check environment credentials
        email = os.getenv("MONARCH_EMAIL")
        password = os.getenv("MONARCH_PASSWORD")
        
        if not email or not password:
            raise RuntimeError("🔐 Authentication needed! Run: cd /Users/arthur/Dev/monarch-mcp-server-py && python login_setup.py")
    
    return _monarch_client


@mcp.tool()
async def check_auth_status() -> str:
    """Check if already authenticated with Monarch Money."""
    try:
        session_locations = [
            os.getenv("MONARCH_SESSION_FILE", "monarch_session.json"),
            "/Users/arthur/Dev/monarch-mcp-server-py/monarch_session.json",
            "/Users/arthur/Dev/monarch-mcp-server-py/.mm/mm_session.pickle",
            os.path.expanduser("~/.mm/mm_session.pickle")
        ]
        
        status = "🔍 Session file check:\n"
        for session_file in session_locations:
            if os.path.exists(session_file):
                status += f"✅ Found: {session_file}\n"
            else:
                status += f"❌ Missing: {session_file}\n"
        
        # Try to load client
        try:
            client = get_monarch_client_sync()
            # Test the connection
            accounts = await client.get_accounts()
            if accounts and "accounts" in accounts:
                status += f"\n✅ Connection successful! Found {len(accounts['accounts'])} accounts."
            else:
                status += "\n⚠️ Connected but no accounts found."
        except Exception as e:
            status += f"\n❌ Connection failed: {str(e)}"
        
        return status
    except Exception as e:
        return f"Error checking auth status: {str(e)}"


@mcp.tool()
async def get_accounts() -> str:
    """Get all financial accounts from Monarch Money."""
    try:
        client = get_monarch_client_sync()
        accounts = await client.get_accounts()
        
        # Format accounts for display
        account_list = []
        for account in accounts.get("accounts", []):
            account_type = account.get("type", {})
            institution = account.get("institution", {})
            account_info = {
                "id": account.get("id"),
                "name": account.get("displayName", account.get("name")),
                "type": account_type.get("name") if isinstance(account_type, dict) else None,
                "balance": account.get("currentBalance"),
                "institution": institution.get("name") if isinstance(institution, dict) else None,
                "is_active": account.get("isActive", True)
            }
            account_list.append(account_info)
        
        return json.dumps(account_list, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to get accounts: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error getting accounts: {str(e)}"


@mcp.tool()
async def get_transactions(
    limit: int = 100,
    offset: int = 0,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    account_id: Optional[str] = None
) -> str:
    """Get transactions from Monarch Money."""
    try:
        client = get_monarch_client_sync()
        
        # Build filters
        filters = {}
        if start_date:
            filters["startDate"] = start_date
        if end_date:
            filters["endDate"] = end_date
        if account_id:
            filters["accountId"] = account_id
        
        transactions = await client.get_transactions(
            limit=limit,
            offset=offset,
            **filters
        )
        
        # Format transactions for display
        transaction_list = []
        for txn in transactions.get("allTransactions", {}).get("results", []):
            transaction_info = {
                "id": txn.get("id"),
                "date": txn.get("date"),
                "amount": txn.get("amount"),
                "description": txn.get("description"),
                "category": txn.get("category", {}).get("name") if txn.get("category") else None,
                "account": txn.get("account", {}).get("displayName"),
                "merchant": txn.get("merchant", {}).get("name") if txn.get("merchant") else None,
                "is_pending": txn.get("isPending", False)
            }
            transaction_list.append(transaction_info)
        
        return json.dumps(transaction_list, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to get transactions: {e}")
        return f"Error getting transactions: {str(e)}"


@mcp.tool()
async def get_budgets() -> str:
    """Get budget information from Monarch Money."""
    try:
        client = get_monarch_client_sync()
        budgets = await client.get_budgets()
        
        # Format budgets for display
        budget_list = []
        for budget in budgets.get("budgets", []):
            budget_info = {
                "id": budget.get("id"),
                "name": budget.get("name"),
                "amount": budget.get("amount"),
                "spent": budget.get("spent"),
                "remaining": budget.get("remaining"),
                "category": budget.get("category", {}).get("name") if budget.get("category") else None,
                "period": budget.get("period")
            }
            budget_list.append(budget_info)
        
        return json.dumps(budget_list, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to get budgets: {e}")
        return f"Error getting budgets: {str(e)}"


@mcp.tool()
async def refresh_accounts() -> str:
    """Request account data refresh from financial institutions."""
    try:
        client = get_monarch_client_sync()
        result = await client.request_accounts_refresh()
        return json.dumps({"success": True, "message": "Account refresh requested", "result": result}, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to refresh accounts: {e}")
        return f"Error refreshing accounts: {str(e)}"


# Export for mcp run
app = mcp

if __name__ == "__main__":
    mcp.run()