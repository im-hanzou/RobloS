import requests
import random
import time
import re
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
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

def print_warning(message: str):
    print(f"{Fore.YELLOW}⚠️  {message}")

def print_separator(char="─", length=60):
    print(Fore.CYAN + char * length)

def fetch_session_csrf_token(session: requests.Session, use_ip_bypass: bool = False) -> bool:
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
            return True
        else:
            return False
            
    except requests.exceptions.RequestException as error:
        if hasattr(error, 'response') and error.response is not None:
            token = error.response.headers.get("x-csrf-token")
            if token:
                session.headers.update({"X-CSRF-TOKEN": token})
                return True
        return False

def generate_auth_ticket(session: requests.Session, use_ip_bypass: bool = False) -> Dict[str, Any]:
    try:
        if not fetch_session_csrf_token(session, use_ip_bypass):
            return {"ticket": "Failed to get CSRF token", "profile": None}
        
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
            
            time.sleep(random.uniform(0.5, 1.5))
        
        session.headers.update({
            "referer": "https://www.roblox.com",
            'Content-Type': 'application/json'
        })
        
        try:
            auth_response = session.get('https://users.roblox.com/v1/users/authenticated')
            auth_response.raise_for_status()
            user_data = auth_response.json()
            profile_url = f"https://www.roblox.com/users/{user_data.get('id', 'Unknown')}/profile"
        except requests.exceptions.RequestException as error:
            if hasattr(error, 'response') and error.response.status_code == 401:
                raise Exception("Current cookie is expired")
            profile_url = None
        
        response = session.post("https://auth.roblox.com/v1/authentication-ticket", json={})
        response.raise_for_status()
        
        ticket = response.headers.get('rbx-authentication-ticket')
        return {
            "ticket": ticket or "Failed to fetch auth ticket",
            "profile": profile_url
        }
        
    except Exception as error:
        if str(error) == "Current cookie is expired":
            return {"ticket": "EXPIRED", "profile": None}
        return {"ticket": "Failed to fetch auth ticket", "profile": None}

def redeem_auth_ticket(auth_ticket: str) -> Dict[str, Any]:
    try:
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
                    return {
                        "success": False,
                        "error": "Failed to get cookie"
                    }
        else:
            new_cookie = cookie_match.group(1)
        
        if not new_cookie or len(new_cookie) < 50:
            return {
                "success": False,
                "error": "Extracted cookie appears incomplete"
            }
        
        return {
            "success": True,
            "refreshed_cookie": new_cookie
        }
        
    except requests.exceptions.RequestException as error:
        error_details = f"{error.response.status_code} {error.response.reason}" if hasattr(error, 'response') else "Unknown error"
        return {
            "success": False,
            "error": str(error),
            "roblox_debug_response": error.response.json() if hasattr(error, 'response') and error.response.content else None
        }

def load_cookies_from_file(filename: str) -> List[str]:
    try:
        if not os.path.exists(filename):
            print_error(f"File {filename} not found!")
            return []
        
        with open(filename, 'r', encoding='utf-8') as f:
            cookies = [line.strip() for line in f.readlines() if line.strip()]
        
        print_success(f"Loaded {len(cookies)} cookies from {filename}")
        return cookies
    except Exception as e:
        print_error(f"Error reading file: {str(e)}")
        return []

def save_refreshed_cookie(cookie: str, profile: str = "", original_cookie: str = "", status: str = "SUCCESS"):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open('refreshed.txt', 'a', encoding='utf-8') as f:
            if status == "SUCCESS":
                f.write(f"Roblox Profile: {profile}\n")
                f.write(f"Cookie: {cookie}\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write("="*60 + "\n\n")
            else:
                f.write(f"FAILED: {original_cookie[:50]}... | {status} | {timestamp}\n")
                
    except Exception as e:
        print_error(f"Error saving to file: {str(e)}")

def refresh_single_cookie(cookie: str, use_bypass: bool = False, proxy: str = None) -> Dict[str, Any]:
    session = requests.Session()
    
    if proxy:
        session.proxies = {
            'http': proxy,
            'https': proxy
        }
    
    session.headers.update({
        'Cookie': f'.ROBLOSECURITY={cookie}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    try:
        auth_data = generate_auth_ticket(session, use_bypass)
        auth_ticket = auth_data["ticket"]
        profile_url = auth_data["profile"]
        
        if auth_ticket == "EXPIRED":
            return {"success": False, "error": "Cookie expired", "profile": None}
        elif auth_ticket in ["Failed to fetch auth ticket", "Failed to get CSRF token"]:
            return {"success": False, "error": auth_ticket, "profile": None}
        
        result = redeem_auth_ticket(auth_ticket)
        if result["success"]:
            result["profile"] = profile_url
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e), "profile": None}
    finally:
        session.close()

def mass_refresh_cookies():
    print_separator("═")
    print(f"{Fore.CYAN}{Style.BRIGHT}🔄 MASS REFRESH MODE")
    print_separator("═")
    
    filename = input(f"{Fore.YELLOW}Enter cookie file name (default: cookies.txt): {Fore.WHITE}").strip()
    if not filename:
        filename = "cookies.txt"
    
    cookies = load_cookies_from_file(filename)
    if not cookies:
        return
    
    proxy = input(f"{Fore.YELLOW}Enter proxy (http://user:pass@host:port or Enter for no proxy): {Fore.WHITE}").strip()
    if proxy and not proxy.startswith('http'):
        proxy = f"http://{proxy}"
    
    use_bypass = input(f"{Fore.YELLOW}Use IP bypass? (y/n): {Fore.WHITE}").strip().lower() == 'y'
    
    print_separator("═")
    print(f"{Fore.CYAN}Starting mass refresh...")
    print(f"{Fore.BLUE}Total cookies: {len(cookies)}")
    print(f"{Fore.BLUE}Proxy: {'Enabled' if proxy else 'Disabled'}")
    print(f"{Fore.BLUE}IP Bypass: {'Enabled' if use_bypass else 'Disabled'}")
    print_separator("═")
    
    success_count = 0
    failed_count = 0
    
    for i, cookie in enumerate(cookies, 1):
        print(f"\n{Fore.CYAN}[{i}/{len(cookies)}] Processing cookie {i}...")
        
        if proxy:
            print_info(f"Using proxy: {proxy}")
        
        result = refresh_single_cookie(cookie, use_bypass, proxy)
        
        if result["success"]:
            print_success(f"Cookie {i} refreshed successfully!")
            print_info(f"Profile: {result.get('profile', 'Unknown')}")
            save_refreshed_cookie(result["refreshed_cookie"], result.get('profile', 'Unknown'))
            success_count += 1
        else:
            print_error(f"Cookie {i} failed: {result['error']}")
            save_refreshed_cookie("", "", cookie, result['error'])
            failed_count += 1
    
    print_separator("═")
    print(f"{Fore.GREEN}{Style.BRIGHT}MASS REFRESH COMPLETED!")
    print(f"{Fore.GREEN}✅ Success: {success_count}")
    print(f"{Fore.RED}❌ Failed: {failed_count}")
    print(f"{Fore.BLUE}📁 Results saved to: refreshed.txt")
    print_separator("═")

def get_user_input():
    print_separator()
    print(f"{Fore.WHITE}Enter your cookie (without .ROBLOSECURITY=)")
    print_separator()
    
    cookie = input(f"{Fore.YELLOW}ROBLOSECURITY Cookie: {Fore.WHITE}").strip()
    
    if not cookie:
        print_error("No cookie provided!")
        return None, None, None
    
    proxy = input(f"{Fore.YELLOW}Enter proxy (http://user:pass@host:port or Enter for no proxy): {Fore.WHITE}").strip()
    if proxy and not proxy.startswith('http'):
        proxy = f"http://{proxy}"
    
    use_bypass = input(f"{Fore.YELLOW}Use IP bypass? (y/n): {Fore.WHITE}").strip().lower() == 'y'
    
    return cookie, use_bypass, proxy

def display_result(result: Dict[str, Any]):
    print_separator("═")
    if result["success"]:
        print(f"{Fore.GREEN}{Style.BRIGHT}🎉 REFRESH SUCCESSFUL!")
        print_separator("═")
        if result.get("profile"):
            print(f"{Fore.CYAN}ROBLOX PROFILE:")
            print(f"{Fore.WHITE}{Style.BRIGHT}{result['profile']}")
            print_separator()
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

def main_menu():
    print_separator("═")
    print(f"{Fore.CYAN}{Style.BRIGHT}SELECT MODE:")
    print(f"{Fore.WHITE}1. Single Cookie Refresh")
    print(f"{Fore.WHITE}2. Mass Cookie Refresh")
    print_separator("═")
    
    choice = input(f"{Fore.YELLOW}Enter your choice (1/2): {Fore.WHITE}").strip()
    return choice

def main():
    print_banner()
    
    try:
        choice = main_menu()
        
        if choice == "1":
            cookie, use_bypass, proxy = get_user_input()
            if not cookie:
                return
            
            print_separator("═")
            print(f"{Fore.CYAN}{Style.BRIGHT}Starting refresh process...")
            print_separator("═")
            
            result = refresh_single_cookie(cookie, use_bypass, proxy)
            display_result(result)
            
        elif choice == "2":
            mass_refresh_cookies()
            
        else:
            print_error("Invalid choice!")
    
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Process interrupted by user.")
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()
