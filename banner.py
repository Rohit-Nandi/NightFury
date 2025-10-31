from datetime import datetime
import pyfiglet
from colorama import Fore, Style, init

init(autoreset=True)

def print_banner():
    # ASCII art for tool name
    fig = pyfiglet.Figlet(font="slant")
    ascii_art = fig.renderText("NightFury")

    # ASCII art for tagline
    fig2 = pyfiglet.Figlet(font="cybermedium")
    tag = fig2.renderText("Command the Night")

    # Print ASCII art in color line by line
    for line in ascii_art.split("\n"):
        print(Fore.RED + Style.BRIGHT + line)
    for line in tag.split("\n"):
        print(Fore.WHITE + Style.BRIGHT + line)

    # Metadata
    print(Fore.WHITE + "=" * 100)
    print(Fore.RED + "Author : Rohit")
    print(Fore.RED + "Version: 1.0")
    print(Fore.RED + f"Date   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(Fore.WHITE + "=" * 100)

if __name__ == "__main__":
    print_banner()
