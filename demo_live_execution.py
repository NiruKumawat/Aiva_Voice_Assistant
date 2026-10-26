"""
Live Execution Runner for User Verification.
Performs live actions directly on the user's screen so they can visually observe:
1. Browser opening YouTube.
2. Smooth cursor gliding to search box with visual click ripple.
3. Typing 'Shape of You by Ed Sheeran' and pressing Enter.
4. Clicking the video to play.
5. Pausing video.
6. Resuming video.
7. Muting for 3 seconds, then unmuting.
8. Setting volume to 50%.
"""

import time
import webbrowser
from PySide6.QtWidgets import QApplication
from computer.controller import ComputerController
from ui.action_indicator import init_action_indicator, show_click_indicator
from utils.logger import logger


def run_live_demo():
    print("=" * 60)
    print("  STARTING LIVE ACTION EXECUTION")
    print("  You can now sit back and watch your screen!")
    print("=" * 60)

    # Initialize Qt for real-time visual click ripples
    app = QApplication.instance()
    if not app:
        app = QApplication([])

    indicator = init_action_indicator()
    controller = ComputerController()

    # Step 1: Open YouTube in the user's actual browser
    print("\n[Step 1] Opening YouTube in browser...")
    webbrowser.open("https://www.youtube.com")
    time.sleep(4.0)  # Allow browser and page to render

    # Step 2: Smooth cursor movement to YouTube search bar and click
    screen_w = controller.mouse.screen_width
    screen_h = controller.mouse.screen_height
    search_x = int(screen_w * 0.48)
    search_y = int(screen_h * 0.09)

    print(f"\n[Step 2] Moving cursor to YouTube Search Bar at ({search_x}, {search_y}) [screen: {screen_w}x{screen_h}]...")
    controller.click(search_x, search_y)
    app.processEvents()
    time.sleep(0.8)

    # Step 3: Type search query
    query = "Shape of You by Ed Sheeran"
    print(f"\n[Step 3] Typing search query: '{query}'...")
    controller.type_text(query, interval=0.04)
    time.sleep(0.5)

    # Step 4: Press Enter
    print("\n[Step 4] Pressing Enter to search...")
    controller.press("enter")
    time.sleep(3.5)  # Wait for YouTube search results to load

    # Step 5: Click first video result scaled to screen resolution
    video_x = int(screen_w * 0.38)
    video_y = int(screen_h * 0.30)
    print(f"\n[Step 5] Clicking official video result at ({video_x}, {video_y})...")
    controller.click(video_x, video_y)
    app.processEvents()
    time.sleep(4.0)  # Wait for video page and playback to start

    # Step 6: Pause the video (YouTube shortcut 'k')
    print("\n[Step 6] Pausing the video (pressing 'k')...")
    controller.press("k")
    time.sleep(2.0)

    # Step 7: Play the video again (YouTube shortcut 'k')
    print("\n[Step 7] Playing the video again (pressing 'k')...")
    controller.press("k")
    time.sleep(2.5)

    # Step 8: Mute the video for 3 seconds, then unmute
    print("\n[Step 8] Muting video (pressing 'm')...")
    controller.press("m")
    time.sleep(3.0)
    print("           Unmuting video (pressing 'm')...")
    controller.press("m")
    time.sleep(2.0)

    # Step 9: Set volume to 50% (YouTube volume key '5')
    print("\n[Step 9] Setting volume to 50% (pressing '5')...")
    controller.press("5")
    time.sleep(1.5)

    print("\n" + "=" * 60)
    print("  LIVE EXECUTION COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_live_demo()
