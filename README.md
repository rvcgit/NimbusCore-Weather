# NimbusCore-Weather
 Ultra-Lightweight Cross-Platform Weather &amp; Lunar Engine
# Ultra-Lightweight Cross-Platform Weather & Lunar Engine

A high-performance, resource-efficient weather dashboard core designed for minimalist desktop panels (like **Rainmeter** on Windows or **Waybar/dzen/lemonbar/polybar/conky etc** on Linux/BSD). can use the output dump from /tmp to pipe data.

Unlike traditional desktop widgets that cause micro-stutters by constantly processing calculations in the UI layer, this project **decouples the engine from the interface**. For 14 minutes and 59 seconds out of every 15 minutes, the background loop uses **exactly 0.00% CPU and 0 MB of RAM**, keeping your system light, efficient, and gaming-responsive.

## ✨ Features
* **Zero UI Overhead:** Separates data parsing from visual rendering.
* **Smart Caching:** Saves raw JSON payloads and Moon phases natively to the system's temporary directory.
* **Beautiful Typography:** Native support for `JetBrainsMono NF` (Nerd Font) weather and directional wind compass glyphs.
* **Rich Hover Forecast:** Pipes a deep 2-day maximum/minimum forecast directly to your cursor hover loop.
* **Cross-Platform Architecture:** Dynamically switches temporary directory paths across Windows, Linux, macOS, and BSD systems.

---

## ️ Project Directory Layout

### 犯 Windows Configuration
On Windows, the backend scripts reside in a dedicated apps folder, while the layout file sits in your user documentation directory:

```text
C:\
└── apps\
    ├── weather_fetcher.bat   # Silent background scheduler loop
    └── weather_fetcher_X_platform.py  OR weather_fetch_X_platform-auto.py        # Core Python weather data parser
    
Documents\Rainmeter\Skins\
└── WeatherCacheSkin\
    └── WeatherCacheSkin.ini # The frosted cloud desktop widget
```

###  Linux /  BSD Configuration
For *nix power users, the Python script can be dropped anywhere in your local binary path, feeding your favorite bar component via standard system temporary directories: EDIT THE weather_fetcher_X_platform.py FIRST, with your LAT/LON Cordinates in the top config section.

```text
~/.local/bin/ or /usr/local/bin/
└── weather.py             # Executed via cron or systemd/run-it services

/tmp/WeatherCache/         # Dynamic cross-platform scratchpad memory
├── weather_api_cache.json # Raw metrics JSON
└── weather_moon_phase     # Text file containing current lunar phase text string
```

---

## ️ Step 1: Install Dependencies

Before running the engine, you must ensure Python 3 and the required network library are installed on your operating system.

### 犯 Windows Setup
1. Download and install [Python 3](https://python.org) (Make sure to check the box that says **"Add Python to PATH"** during installation).
2. Open your Command Prompt (`cmd`) or PowerShell and install the required library:
   ```cmd
   pip install requests
   ```

###  Linux /  BSD Setup
Install Python 3 and pip via your system package manager, then fetch the network package:
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3 python3-pip
pip3 install requests

# Fedora/RHEL
sudo dnf install python3 python3-pip
pip3 install requests

# Arch Linux
sudo pacman -S python-requests

# FreeBSD / OpenBSD
sudo pkg install python3 py39-requests
```

---

##  Step 2: Automation Setup (Running in the Background)

The engine loops dynamically every 15 minutes to pull fresh data from the Open-Meteo API.

### 犯 Windows (Task Scheduler Setup)
To prevent a distracting black console window from staying open on your screen, automate it quietly via Windows Task Scheduler:

1. Download file named `weather_fetcher.bat`**[ edit file to weather_fetch_X_platform-auto.py for auto LAT/LON in the bat file ]** inside `C:\apps\`.
2. Open **Task Scheduler** -> Click **Create Task...** (In the right-hand panel).
4. **General:** Name it `WeatherEngineAutomator`, check **Run with highest privileges**, and select **Run whether user is logged on or not**, and select **Hidden** (this completely hides the command prompt window).
5. **Triggers:** Add a new trigger set to **At log on**.
6. **Actions:** Set to **Start a program**, browse to your `weather_fetcher.bat`, and fill in the **Start in** field with its parent folder path (`C:\apps`).
7. Save the task and enter your Windows account password when prompted.
8. ALTERNATIVE TO ALL ABOVE TASK SCHEDULER EXERCISE, USE run_silently.vbs and place it in windows startup folder
8. **Wait a couple of minutes for the skin to refresh. it reads from the populated "CACHE"**


##  Step 3: Rainmeter Desktop Integration (Windows)

1. Make sure you have the [JetBrainsMono Nerd Font](https://github.com) installed system-wide on your Windows machine.
2. Create a folder named `WeatherCacheSkin` inside your Rainmeter Skins path (`Documents\Rainmeter\Skins\`).
3. Download `WeatherCacheSkin.ini` from this repository, place it in your WeatherCache Folder [ \Rainmeter\Skns\WeatherCache\
4. Open your **Rainmeter Manager**, click **Refresh all**, select the skin file, and hit **Load**.
5. Hover your cursor over the main temperature readout to reveal the comprehensive, high-contrast 2-day forecast popup
   window!

   
##### For the *nix users, simply clone the weather_fetcher_X_platform.py OR weather_fetch_X_platform-auto.py; make it executable with chmod a+x; place it in your $PATH 
[ $HOME/.bin/ as the file is configured in my setup ]

Then create a shell script to execute this python file using command "python3 ~/.bin/weather_fetcher_X_platform.py" with a "while ; do loop for say 1200 seconds so every 20 min this script will fetch data and dump to /tmp. [ weather_icon_cache ; weather_temp_cache ; weather_moon_phase ; weather_api_cache.json ; windspeed ] use this to pipe data to dzen panel OR conky or Waybar or polybar etc. dont forget to have a look at the preview provided

example while loop script to run on startup:
open your text editor and create a bash script named weather_refresh and copy the contents as below: [ for 15 min loop ]
~~~text
#!/usr/bin/env bash
while : ; do python3 $HOME/.bin/YOUR_WEATHER_FETCHER.py file you have cloned; sleep 900 ; done
~~~
save it, make it executable by 'chmod a+x ~/.bin/weather_refresh' command in the terminal. add this script at your autostart.

[PREVIEW](https://github.com/rvcgit/NimbusCore-Weather/blob/main/NimbusCoreWeather.png)  

[RAINMETER PREVIEW](https://github.com/rvcgit/NimbusCore-Weather/blob/main/Preview_2.PNG)


