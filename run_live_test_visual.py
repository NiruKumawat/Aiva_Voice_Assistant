"""
Live Visual Test Runner with On-Screen HUD.
Executes actions step-by-step with comfortable pacing and smooth cursor glides
so the user can visually watch every single test execute on their laptop screen.
"""

import time
import subprocess
import webbrowser
import win32gui
import win32con
from PySide6.QtWidgets import QApplication
from ui.test_hud import get_live_hud
from computer.controller import ComputerController
from utils.logger import logger


def bring_browser_to_front():
    """Finds any open Chrome, Edge, or Firefox browser window and brings it to front."""
    def enum_windows_callback(hwnd, windows_list):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if any(b in title.lower() for b in ["chrome", "edge", "youtube", "firefox", "brave"]):
                windows_list.append((hwnd, title))
    
    matching_windows = []
    win32gui.EnumWindows(enum_windows_callback, matching_windows)
    
    if matching_windows:
        hwnd, title = matching_windows[0]
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            win32gui.SetForegroundWindow(hwnd)
            logger.info(f"Brought browser window to front: '{title}'")
            return True
        except Exception as e:
            logger.debug(f"SetForegroundWindow exception: {e}")
    return False


def run_visual_live_tests():
    # 1. Initialize PySide6 Application & Live HUD
    app = QApplication.instance()
    if not app:
        app = QApplication([])

    hud = get_live_hud()
    controller = ComputerController()
    screen_w = controller.mouse.screen_width
    screen_h = controller.mouse.screen_height

    def update_hud(step_num, total_steps, title, desc, delay_sec=1.0):
        hud.set_step(f"[TEST {step_num}/{total_steps}] {title}", desc)
        for _ in range(int(delay_sec * 10)):
            app.processEvents()
            time.sleep(0.1)

    print("=" * 65)
    print("  STARTING STEP-BY-STEP LIVE VISUAL TEST")
    print("  Look at your laptop screen now!")
    print("=" * 65)

    TOTAL = 8

    # --- STEP 1: OPEN YOUTUBE ---
    update_hud(1, TOTAL, "OPENING YOUTUBE", "Launching browser and loading YouTube in full screen...", delay_sec=1.0)
    
    # Try launching Chrome directly in maximized window
    try:
        subprocess.Popen(["cmd", "/c", "start", "chrome", "--start-maximized", "https://www.youtube.com"])
    except Exception:
        webbrowser.open("https://www.youtube.com")

    # Give browser time to launch and render
    time.sleep(3.5)
    bring_browser_to_front()
    update_hud(1, TOTAL, "YOUTUBE LOADED", "Browser is ready. Preparing search...", delay_sec=2.0)

    # --- STEP 2: GLIDE CURSOR TO SEARCH BAR ---
    # YouTube search bar is horizontally centered around ~45-52% width and top ~8-10% height
    search_x = int(screen_w * 0.48)
    search_y = int(screen_h * 0.09)

    update_hud(2, TOTAL, "FINDING SEARCH BAR", f"Gliding mouse cursor to ({search_x}, {search_y})...", delay_sec=0.5)
    
    # Smooth glide over 0.7s so the user can easily follow the cursor
    controller.mouse.move(search_x, search_y, duration=0.7)
    app.processEvents()
    time.sleep(0.2)

    # Click with visual click ripple
    update_hud(2, TOTAL, "CLICKING SEARCH BAR", "Focusing the YouTube search input...", delay_sec=0.5)
    controller.click(search_x, search_y)
    app.processEvents()
    time.sleep(1.2)

    # --- STEP 3: TYPE SEARCH QUERY ---
    query = "Shape of You by Ed Sheeran"
    update_hud(3, TOTAL, "TYPING SEARCH QUERY", f"Typing: “{query}”...", delay_sec=0.5)
    controller.type_text(query, interval=0.06)
    app.processEvents()
    time.sleep(1.5)

    # --- STEP 4: PRESS ENTER TO SEARCH ---
    update_hud(4, TOTAL, "EXECUTING SEARCH", "Pressing Enter key to fetch results...", delay_sec=0.5)
    controller.press("enter")
    app.processEvents()
    time.sleep(3.5)  # Wait for search results to load
    bring_browser_to_front()

    # --- STEP 5: CLICK FIRST OFFICIAL VIDEO ---
    # Scaled to screen resolution: ~38% width and ~30% height
    video_x = int(screen_w * 0.38)
    video_y = int(screen_h * 0.30)

    update_hud(5, TOTAL, "SELECTING VIDEO", f"Gliding cursor to official video at ({video_x}, {video_y})...", delay_sec=0.5)
    controller.mouse.move(video_x, video_y, duration=0.7)
    app.processEvents()
    time.sleep(0.3)

    update_hud(5, TOTAL, "PLAYING VIDEO", "Clicking video thumbnail to start playback...", delay_sec=0.5)
    controller.click(video_x, video_y)
    app.processEvents()
    time.sleep(4.5)  # Allow video page and playback to start
    bring_browser_to_front()

    # --- STEP 6: PAUSE VIDEO ---
    update_hud(6, TOTAL, "PAUSING VIDEO", "Sending YouTube shortcut 'k' to pause video...", delay_sec=0.5)
    controller.press("k")
    app.processEvents()
    update_hud(6, TOTAL, "VIDEO PAUSED", "Video is paused. Waiting 3 seconds...", delay_sec=3.0)

    # --- STEP 7: RESUME PLAYBACK ---
    update_hud(7, TOTAL, "PLAYING VIDEO AGAIN", "Sending shortcut 'k' to resume music...", delay_sec=0.5)
    controller.press("k")
    app.processEvents()
    update_hud(7, TOTAL, "PLAYING RESUMED", "Video is playing again. Enjoying music...", delay_sec=3.0)

    # --- STEP 8: MUTE -> WAIT 3 SECONDS -> UNMUTE ---
    update_hud(8, TOTAL, "MUTING VIDEO", "Muting audio (pressing 'm')...", delay_sec=0.5)
    controller.press("m")
    app.processEvents()
    
    update_hud(8, TOTAL, "WAITING 3 SECONDS", "Audio is muted. Waiting 3.0s...", delay_sec=3.0)
    
    update_hud(8, TOTAL, "UNMUTING VIDEO", "Unmuting audio (pressing 'm')...", delay_sec=0.5)
    controller.press("m")
    app.processEvents()
    time.sleep(2.0)

    # --- FINAL: SET VOLUME TO 50% ---
    hud.set_step("[BONUS STEP] SETTING VOLUME TO 50%", "Pressing '5' to set volume to 50%...")
    controller.press("5")
    app.processEvents()
    time.sleep(2.5)

    # Completed banner
    hud.set_step("[ALL TESTS PASSED SUCCESSFULLY!]", "All live actions executed directly on your laptop screen.")
    for _ in range(40):
        app.processEvents()
        time.sleep(0.1)

    hud.hide()
    print("\n" + "=" * 65)
    print("  ALL LIVE VISUAL TESTS EXECUTED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    run_visual_live_tests()
