import requests
import random
import time
import re
import json
from typing import Optional, Dict, Any
from colorama import init, Fore, Back, Style

init(autoreset=True)

def print_banner():
    banner = """
╔═══════════════════════════════════════════════╗
║           Roblox Cookie Refresher             ║
║     Github: https://github.com/im-hanzou      ║
╚═══════════════════════════════════════════════╝
    """
    print(Fore.CYAN + banner)

def print_success(message: str):
    print(f"{Fore.GREEN}✅ {message}")

def print_error(message: str):
    print(f"{Fore.RED}❌ {message}")

def print_info(message: str):
    print(f"{Fore.BLUE}ℹ️  {message}")

def print_progress(message: str):
    print(f"{Fore.MAGENTA}🔄 {message}")

def print_separator(char="─", length=60):
    print(Fore.CYAN + char * length)

def fetch_session_csrf_token(session: requests.Session, use_ip_bypass: bool = False) -> bool:
    print_progress("Fetching X-CSRF-TOKEN...")
    
    if use_ip_bypass:
        random_ip = f"{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
        session.headers.update({
            'X-Forwarded-For': random_ip,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Cache-Control': 'no-cache',
            'Accept-Language': 'en-US,en;q=0.9'
        })
    
    try:
        resp = session.post("https://auth.roblox.com/v2/logout")
        token = resp.headers.get("x-csrf-token")
        
        if token:
            session.headers.update({"X-CSRF-TOKEN": token})
            print_success(f"X-CSRF-TOKEN obtained successfully!")
            return True
        else:
            print_error("Failed to fetch X-CSRF-TOKEN")
            return False
            
    except requests.exceptions.RequestException as error:
        if hasattr(error, 'response') and error.response is not None:
            token = error.response.headers.get("x-csrf-token")
            if token:
                session.headers.update({"X-CSRF-TOKEN": token})
                print_success("X-CSRF-TOKEN obtained from error response!")
                return True
        
        print_error(f"Error fetching CSRF token: {str(error)}")
        return False

def generate_auth_ticket(session: requests.Session, use_ip_bypass: bool = False) -> str:
    try:
        if use_ip_bypass:
            print_info("Using IP bypass mode")
        
        if not fetch_session_csrf_token(session, use_ip_bypass):
            return "Failed to get CSRF token"
        
        if use_ip_bypass:
            random_client_id = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
            random_ip = f"{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
            
            session.headers.update({
                'Accept-Language': f'en-US,en;q={random.uniform(0.1, 0.9):.1f}',
                'Cache-Control': 'no-cache',
                'Pragma': f'no-cache-{random_client_id}',
                'X-Forwarded-For': random_ip,
                'X-Real-IP': random_ip,
                'Connection': random.choice(['keep-alive', 'close']),
                'Viewport-Width': str(800 + random.randint(0, 1000))
            })
            
            print_info(f"Bypass fingerprint: {random_client_id}")
            time.sleep(random.uniform(0.5, 1.5))
        
        session.headers.update({
            "referer": "https://www.roblox.com",
            'Content-Type': 'application/json'
        })
        
        print_progress("Validating cookie...")
        try:
            auth_response = session.get('https://users.roblox.com/v1/users/authenticated')
            auth_response.raise_for_status()
            user_data = auth_response.json()
            print_success(f"Cookie valid - Roblox profile: https://www.roblox.com/users/{user_data.get('id', 'Unknown')}/profile")
        except requests.exceptions.RequestException as error:
            if hasattr(error, 'response') and error.response.status_code == 401:
                print_error("Cookie has expired")
                raise Exception("Current cookie is expired")
            print_error(f"Cookie validation failed: {error}")
        
        print_progress("Requesting authentication ticket...")
        response = session.post("https://auth.roblox.com/v1/authentication-ticket", json={})
        response.raise_for_status()
        
        ticket = response.headers.get('rbx-authentication-ticket')
        if ticket:
            print_success("Authentication ticket generated!")
        else:
            print_error("Failed to generate authentication ticket")
        
        return ticket or "Failed to fetch auth ticket"
        
    except Exception as error:
        if str(error) == "Current cookie is expired":
            return "EXPIRED"
        print_error(f"Error generating auth ticket: {str(error)}")
        return "Failed to fetch auth ticket"

def redeem_auth_ticket(auth_ticket: str) -> Dict[str, Any]:
    try:
        print_progress("Redeeming authentication ticket...")
        
        response = requests.post("https://auth.roblox.com/v1/authentication-ticket/redeem", 
                               json={"authenticationTicket": auth_ticket},
                               headers={'RBXAuthenticationNegotiation': '1'})
        response.raise_for_status()
        
        set_cookie_header = response.headers.get('set-cookie', '')
        
        cookie_pattern = r'(_\|WARNING:-DO-NOT-SHARE-THIS\.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items\.\|_[^;,\s]+)'
        cookie_match = re.search(cookie_pattern, set_cookie_header)
        
        if not cookie_match:
            cookie_pattern_alt = r'\.ROBLOSECURITY=([^;,\s]+)'
            cookie_match = re.search(cookie_pattern_alt, set_cookie_header)
            if cookie_match:
                new_cookie = cookie_match.group(1)
            else:
                cookie_parts = set_cookie_header.split('.ROBLOSECURITY=')
                if len(cookie_parts) > 1:
                    cookie_value = cookie_parts[1].split(';')[0].split(',')[0].strip()
                    new_cookie = cookie_value
                else:
                    print_error("Failed to extract cookie from response")
                    print_info(f"Set-Cookie Header: {set_cookie_header[:200]}...")
                    return {
                        "success": False,
                        "error": "Failed to get cookie"
                    }
        else:
            new_cookie = cookie_match.group(1)
        
        if not new_cookie or len(new_cookie) < 50:  
            print_error(f"Extracted cookie seems too short: {len(new_cookie)} characters")
            print_info(f"Cookie preview: {new_cookie[:50]}...")
            return {
                "success": False,
                "error": "Extracted cookie appears incomplete"
            }
        
        print_success("Cookie refreshed successfully!")
        print_info(f"New cookie length: {len(new_cookie)} characters")
        
        return {
            "success": True,
            "refreshed_cookie": new_cookie
        }
        
    except requests.exceptions.RequestException as error:
        error_details = f"{error.response.status_code} {error.response.reason}" if hasattr(error, 'response') else "Unknown error"
        print_error(f"Redemption failed: {error_details}")
        
        return {
            "success": False,
            "error": str(error),
            "roblox_debug_response": error.response.json() if hasattr(error, 'response') and error.response.content else None
        }

def get_user_input():
    print_separator()
    print(f"{Fore.WHITE}Enter your cookie (without .ROBLOSECURITY=)")
    print_separator()
    
    cookie = input(f"{Fore.YELLOW}ROBLOSECURITY Cookie: {Fore.WHITE}").strip()
    
    if not cookie:
        print_error("No cookie provided!")
        return None, None
    
    use_bypass = input(f"{Fore.YELLOW}Use IP bypass? (y/n): {Fore.WHITE}").strip().lower() == 'y'
    
    return cookie, use_bypass

def display_result(result: Dict[str, Any]):
    print_separator("═")
    if result["success"]:
        print(f"{Fore.GREEN}{Style.BRIGHT}🎉 REFRESH SUCCESSFUL!")
        print_separator("═")
        print(f"{Fore.CYAN}REFRESHED COOKIE:")
        print_separator()
        print(f"{Fore.WHITE}{Style.BRIGHT}{result['refreshed_cookie']}")
        print_separator("═")
    else:
        print(f"{Fore.RED}{Style.BRIGHT}❌ REFRESH FAILED!")
        print_separator()
        print_error(f"Reason: {result['error']}")
        if result.get('roblox_debug_response'):
            print_info(f"Debug: {result['roblox_debug_response']}")

def main():
    print_banner()
    
    try:
        cookie, use_bypass = get_user_input()
        if not cookie:
            return
        
        print_separator("═")
        print(f"{Fore.CYAN}{Style.BRIGHT}Starting refresh process...")
        print_separator("═")
        
        session = requests.Session()
        session.headers.update({
            'Cookie': f'.ROBLOSECURITY={cookie}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        auth_ticket = generate_auth_ticket(session, use_bypass)
        
        if auth_ticket == "EXPIRED":
            print_error("Your cookie has expired!")
            return
        elif auth_ticket in ["Failed to fetch auth ticket", "Failed to get CSRF token"]:
            print_error(auth_ticket)
            return
        
        print_info(f"Ticket preview: {auth_ticket[:30]}...")
        print_separator()
        
        result = redeem_auth_ticket(auth_ticket)
        display_result(result)
    
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Process interrupted by user.")
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
    finally:
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    main()
