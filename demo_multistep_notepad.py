"""
Demo Runner for Multi-Step Reasoning & Chained Workflow Execution:
"open notepad take new file and write palindrome code"

Demonstrates:
1. Multi-step reasoning decomposition (App Launch -> Focus Wait -> New File -> Code Generation & Instant Pasting).
2. Safe window focus transition (safety manager seamlessly follows the newly launched application).
3. Instant, indentation-perfect code typing via clipboard injection.
"""

import time
from agent.loop import AgentLoop
from utils.logger import logger

def main():
    print("=" * 65)
    print("  DEMO: MULTI-STEP REASONING & CHAINED EXECUTION")
    print("  Instruction: 'open notepad take new file and write palindrome code'")
    print("=" * 65)

    def on_status(status_text):
        print(f"  [HUD Status] -> {status_text}")

    def on_tts(speech_text):
        print(f"  [Voice Response] -> \"{speech_text}\"")

    agent = AgentLoop(status_callback=on_status, tts_callback=on_tts)

    user_query = "open notepad take new file and write palindrome code"
    print(f"\nDispatching user voice command: '{user_query}'...\n")

    t_start = time.perf_counter()
    answer = agent.run_cycle(user_query)
    elapsed = time.perf_counter() - t_start

    print("\n" + "=" * 65)
    print(f"  CYCLE COMPLETED in {elapsed:.2f} seconds!")
    print(f"  Final Spoken Response: \"{answer}\"")
    print("=" * 65)

if __name__ == "__main__":
    main()
