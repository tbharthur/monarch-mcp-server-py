#!/usr/bin/env python3
"""
Improved Monarch Money login script that saves sessions to multiple locations.
This ensures the MCP server can always find a valid session.
"""

import asyncio
import os
import getpass
import shutil
from pathlib import Path
from monarchmoney import MonarchMoney, RequireMFAException
from dotenv import load_dotenv

async def save_session_everywhere(mm: MonarchMoney) -> bool:
    """Save session to all locations where MCP server might look."""
    
    locations = [
        "monarch_session.json",  # Primary location
        ".mm/mm_session.pickle",  # Secondary location
        Path.home() / ".mm" / "mm_session.pickle"  # User home location
    ]
    
    success_count = 0
    
    for location in locations:
        try:
            # Create directory if needed
            location = Path(location)
            location.parent.mkdir(parents=True, exist_ok=True)
            
            # Save session
            mm.save_session(str(location))
            
            if location.exists():
                size = location.stat().st_size
                print(f"  ✓ Saved to {location} ({size} bytes)")
                success_count += 1
            else:
                print(f"  ✗ Failed to save to {location}")
                
        except Exception as e:
            print(f"  ✗ Error saving to {location}: {e}")
    
    return success_count > 0

async def test_session(mm: MonarchMoney) -> bool:
    """Test if the session works."""
    try:
        accounts = await mm.get_accounts()
        if accounts and "accounts" in accounts:
            count = len(accounts.get("accounts", []))
            print(f"✅ Session valid - found {count} accounts")
            return True
    except Exception as e:
        print(f"❌ Session test failed: {e}")
    return False

async def main():
    load_dotenv()
    
    print("\n🏦 Monarch Money - Improved Authentication Setup")
    print("=" * 50)
    print("This script saves your session to multiple locations")
    print("ensuring it works reliably with Claude Desktop.\n")
    
    mm = MonarchMoney()
    authenticated = False
    
    # First, try to load existing session
    existing_locations = [
        "monarch_session.json",
        ".mm/mm_session.pickle",
        str(Path.home() / ".mm" / "mm_session.pickle")
    ]
    
    print("Checking for existing sessions...")
    for location in existing_locations:
        if Path(location).exists():
            try:
                mm.load_session(location)
                print(f"  Found session at {location}")
                if await test_session(mm):
                    print("✅ Existing session is still valid!")
                    authenticated = True
                    break
            except:
                pass
    
    # If no valid session, authenticate
    if not authenticated:
        print("\n📝 No valid session found. Please log in:\n")
        
        email = input("Email: ")
        password = getpass.getpass("Password: ")
        
        print("\nAuthenticating...")
        
        try:
            # Try normal login
            await mm.login(email, password)
            print("✅ Login successful (no MFA required)")
            authenticated = True
            
        except RequireMFAException:
            print("🔐 MFA required")
            mfa_code = input("Two Factor Code: ")
            
            # Create new instance for MFA
            mm_mfa = MonarchMoney()
            await mm_mfa.multi_factor_authenticate(email, password, mfa_code)
            print("✅ MFA authentication successful")
            mm = mm_mfa
            authenticated = True
        
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return
    
    # Test the connection
    print("\n🧪 Testing connection...")
    if not await test_session(mm):
        print("❌ Session is not working properly")
        return
    
    # Save session to all locations
    print("\n💾 Saving session to multiple locations...")
    if await save_session_everywhere(mm):
        print("\n🎉 Setup complete! Your session is saved in multiple locations.")
    else:
        print("\n⚠️ Warning: Could not save session to all locations")
    
    print("\n📝 Next steps:")
    print("1. Restart Claude Desktop")
    print("2. The Monarch Money tools should now work:")
    print("   • get_accounts - View all accounts")
    print("   • get_transactions - Recent transactions")
    print("   • get_budgets - Budget information")
    print("\n💡 This session will work for several weeks!")
    
    # Final verification
    print("\n🔍 Final verification...")
    test_mm = MonarchMoney()
    test_mm.load_session("monarch_session.json")
    if await test_session(test_mm):
        print("✅ Everything is working perfectly!")
    else:
        print("⚠️ There might be an issue - please try restarting Claude Desktop")

if __name__ == "__main__":
    asyncio.run(main())