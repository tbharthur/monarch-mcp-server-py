"""Monarch Money MCP Server - Main server implementation."""

import os
import logging
import asyncio
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
import json
import threading
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import mcp.types as types
from monarchmoney import MonarchMoney, RequireMFAException
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Monarch Money MCP Server")

# Global MonarchMoney instance
_monarch_client: Optional[MonarchMoney] = None

def run_async(coro):
    """Run async function in a new thread with its own event loop."""
    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    with ThreadPoolExecutor() as executor:
        future = executor.submit(_run)
        return future.result()


class MonarchConfig(BaseModel):
    """Configuration for Monarch Money connection."""
    email: Optional[str] = Field(default=None, description="Monarch Money email")
    password: Optional[str] = Field(default=None, description="Monarch Money password")
    session_file: str = Field(default="monarch_session.json", description="Session file path")


async def get_monarch_client() -> MonarchMoney:
    """Get or create MonarchMoney client instance."""
    global _monarch_client
    
    if _monarch_client is None:
        _monarch_client = MonarchMoney()
        
        # Debug: print to stderr so it shows in Claude Desktop logs
        import sys
        print(f"DEBUG: Looking for session files...", file=sys.stderr)
        
        # Try to load existing session first - check multiple locations
        session_locations = [
            os.getenv("MONARCH_SESSION_FILE", "monarch_session.json"),
            "/Users/arthur/Dev/monarch-mcp-server-py/monarch_session.json",
            "/Users/arthur/Dev/monarch-mcp-server-py/.mm/mm_session.pickle",
            os.path.expanduser("~/.mm/mm_session.pickle")  # Default library location
        ]
        
        print(f"DEBUG: Session locations to check: {session_locations}", file=sys.stderr)
        
        for session_file in session_locations:
            print(f"DEBUG: Checking {session_file}...", file=sys.stderr)
            if os.path.exists(session_file):
                print(f"DEBUG: Found session file: {session_file}", file=sys.stderr)
                logger.info(f"Found session file: {session_file}")
                try:
                    # Try creating a fresh client and loading the session
                    test_client = MonarchMoney()
                    test_client.load_session(session_file)  # This is NOT async!
                    print(f"DEBUG: Successfully loaded session from: {session_file}", file=sys.stderr)
                    logger.info(f"Successfully loaded Monarch Money session from: {session_file}")
                    _monarch_client = test_client
                    
                    # Test the session works
                    logger.info("Testing session validity...")
                    return _monarch_client
                except Exception as e:
                    logger.error(f"Failed to load session from {session_file}: {e}")
                    logger.error(f"Exception type: {type(e)}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    # Continue to next session file
            else:
                logger.debug(f"Session file not found: {session_file}")
        
        # If no session found, try environment credentials
        email = os.getenv("MONARCH_EMAIL")
        password = os.getenv("MONARCH_PASSWORD")
        
        if email and password:
            try:
                await _monarch_client.login(email, password)
                logger.info("Successfully logged into Monarch Money with environment credentials")
            except Exception as e:
                logger.error(f"Failed to login to Monarch Money: {e}")
                raise
        else:
            raise RuntimeError("🔐 Authentication needed! Run: cd /Users/arthur/Dev/monarch-mcp-server-py && python login_setup.py")
    
    return _monarch_client


@mcp.tool()
def setup_authentication() -> str:
    """Get instructions for setting up secure authentication with Monarch Money."""
    return """🔐 Monarch Money - One-Time Setup

1️⃣ Open Terminal and run:
   cd /Users/arthur/Dev/monarch-mcp-server-py && python login_setup.py

2️⃣ Enter your Monarch Money credentials when prompted
   • Email and password
   • 2FA code if you have MFA enabled

3️⃣ Session will be saved automatically and last for weeks

4️⃣ Start using Monarch tools in Claude Desktop:
   • get_accounts - View all accounts
   • get_transactions - Recent transactions  
   • get_budgets - Budget information

✅ Session persists across Claude restarts
✅ No need to re-authenticate frequently
✅ All credentials stay secure in terminal"""


@mcp.tool()
def check_auth_status() -> str:
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
        
        email = os.getenv("MONARCH_EMAIL")
        if email:
            status += f"\n📧 Environment email: {email}"
        
        status += "\n\n💡 Try get_accounts to test connection or run login_setup.py if needed."
        
        return status
    except Exception as e:
        return f"Error checking auth status: {str(e)}"


@mcp.tool()
def debug_session_loading() -> str:
    """Debug session loading issues."""
    try:
        async def _debug():
            import traceback
            
            session_file = "/Users/arthur/Dev/monarch-mcp-server-py/.mm/mm_session.pickle"
            
            try:
                client = MonarchMoney()
                client.load_session(session_file)  # NOT async!
                return "✅ Session loaded successfully"
            except Exception as e:
                error_details = traceback.format_exc()
                return f"❌ Session loading failed:\nError: {str(e)}\nType: {type(e)}\nTraceback:\n{error_details}"
        
        return run_async(_debug())
    except Exception as e:
        return f"Debug failed: {str(e)}"


@mcp.tool()
def get_accounts() -> str:
    """Get all financial accounts from Monarch Money."""
    try:
        async def _get_accounts():
            client = await get_monarch_client()
            return await client.get_accounts()
        
        accounts = run_async(_get_accounts())
        
        # Format accounts for display
        account_list = []
        for account in accounts.get("accounts", []):
            account_type = account.get("type", {})
            institution = account.get("institution", {})
            account_info = {
                "id": account.get("id"),
                "name": account.get("displayName", account.get("name")),
                "type": account_type.get("name") if account_type else None,
                "balance": account.get("currentBalance"),
                "institution": institution.get("name") if institution else None,
                "is_active": account.get("isActive", True)
            }
            account_list.append(account_info)
        
        return json.dumps(account_list, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to get accounts: {e}")
        return f"Error getting accounts: {str(e)}"


@mcp.tool()
def get_transactions(
    limit: int = 100,
    offset: int = 0,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    account_id: Optional[str] = None
) -> str:
    """
    Get transactions from Monarch Money.
    
    Args:
        limit: Number of transactions to retrieve (default: 100)
        offset: Number of transactions to skip (default: 0)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        account_id: Specific account ID to filter by
    """
    try:
        async def _get_transactions():
            client = await get_monarch_client()
            
            # Build filters
            filters = {}
            if start_date:
                filters["startDate"] = start_date
            if end_date:
                filters["endDate"] = end_date
            if account_id:
                filters["accountId"] = account_id
            
            return await client.get_transactions(
                limit=limit,
                offset=offset,
                **filters
            )
        
        transactions = run_async(_get_transactions())
        
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
def get_budgets() -> str:
    """Get budget information from Monarch Money."""
    try:
        async def _get_budgets():
            client = await get_monarch_client()
            return await client.get_budgets()
        
        budgets = run_async(_get_budgets())
        
        # Format budgets for display
        budget_list = []
        for budget in budgets.get("budgets", []):
            budget_info = {
                "id": budget.get("id"),
                "name": budget.get("name"),
                "amount": budget.get("amount"),
                "spent": budget.get("spent"),
                "remaining": budget.get("remaining"),
                "category": budget.get("category", {}).get("name"),
                "period": budget.get("period")
            }
            budget_list.append(budget_info)
        
        return json.dumps(budget_list, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to get budgets: {e}")
        return f"Error getting budgets: {str(e)}"


@mcp.tool()
def get_cashflow(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """
    Get cashflow analysis from Monarch Money.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    """
    try:
        async def _get_cashflow():
            client = await get_monarch_client()
            
            filters = {}
            if start_date:
                filters["startDate"] = start_date
            if end_date:
                filters["endDate"] = end_date
            
            return await client.get_cashflow(**filters)
        
        cashflow = run_async(_get_cashflow())
        
        return json.dumps(cashflow, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to get cashflow: {e}")
        return f"Error getting cashflow: {str(e)}"


@mcp.tool()
def get_account_holdings(account_id: str) -> str:
    """
    Get investment holdings for a specific account.
    
    Args:
        account_id: The ID of the investment account
    """
    try:
        async def _get_holdings():
            client = await get_monarch_client()
            return await client.get_account_holdings(account_id)
        
        holdings = run_async(_get_holdings())
        
        return json.dumps(holdings, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to get account holdings: {e}")
        return f"Error getting account holdings: {str(e)}"


@mcp.tool()
def create_transaction(
    account_id: str,
    amount: float,
    description: str,
    date: str,
    category_id: Optional[str] = None,
    merchant_name: Optional[str] = None
) -> str:
    """
    Create a new transaction in Monarch Money.
    
    Args:
        account_id: The account ID to add the transaction to
        amount: Transaction amount (positive for income, negative for expenses)
        description: Transaction description
        date: Transaction date in YYYY-MM-DD format
        category_id: Optional category ID
        merchant_name: Optional merchant name
    """
    try:
        async def _create_transaction():
            client = await get_monarch_client()
            
            transaction_data = {
                "accountId": account_id,
                "amount": amount,
                "description": description,
                "date": date
            }
            
            if category_id:
                transaction_data["categoryId"] = category_id
            if merchant_name:
                transaction_data["merchantName"] = merchant_name
            
            return await client.create_transaction(**transaction_data)
        
        result = run_async(_create_transaction())
        
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to create transaction: {e}")
        return f"Error creating transaction: {str(e)}"


@mcp.tool()
def update_transaction(
    transaction_id: str,
    amount: Optional[float] = None,
    description: Optional[str] = None,
    category_id: Optional[str] = None,
    date: Optional[str] = None
) -> str:
    """
    Update an existing transaction in Monarch Money.
    
    Args:
        transaction_id: The ID of the transaction to update
        amount: New transaction amount
        description: New transaction description
        category_id: New category ID
        date: New transaction date in YYYY-MM-DD format
    """
    try:
        async def _update_transaction():
            client = await get_monarch_client()
            
            update_data = {"transactionId": transaction_id}
            
            if amount is not None:
                update_data["amount"] = amount
            if description is not None:
                update_data["description"] = description
            if category_id is not None:
                update_data["categoryId"] = category_id
            if date is not None:
                update_data["date"] = date
            
            return await client.update_transaction(**update_data)
        
        result = run_async(_update_transaction())
        
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to update transaction: {e}")
        return f"Error updating transaction: {str(e)}"


@mcp.tool()
def refresh_accounts() -> str:
    """Request account data refresh from financial institutions."""
    try:
        async def _refresh_accounts():
            client = await get_monarch_client()
            return await client.request_accounts_refresh()
        
        result = run_async(_refresh_accounts())
        
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to refresh accounts: {e}")
        return f"Error refreshing accounts: {str(e)}"


def main():
    """Main entry point for the server."""
    logger.info("Starting Monarch Money MCP Server...")
    try:
        mcp.run()
    except Exception as e:
        logger.error(f"Failed to run server: {str(e)}")
        raise


# Export for mcp run
app = mcp

if __name__ == "__main__":
    main()