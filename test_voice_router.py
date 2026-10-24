import asyncio
import sys
import os

sys.path.insert(0, os.getcwd())

from voice_interface import JarvisVoice


class MockClient:
    """Mock client that records sent commands for verification."""
    def __init__(self):
        self.sent = []

    async def send(self, target, command, args={}):
        self.sent.append({'target': target, 'command': command, 'args': args})
        print(f"    [SENT] target={target}, command={command}, args={args}")


async def test_voice_router():
    client = MockClient()
    voice = JarvisVoice(client)

    # Force wake-word state off so commands route directly
    voice.listening_for_wake = False

    test_cases = [
        # (spoken_phrase, expected_target, expected_command)
        ("system status", "laptop", "sysinfo"),
        ("sysinfo", "laptop", "sysinfo"),
        ("screenshot", "laptop", "screenshot"),
        ("battery", "phone", "battery"),
        ("send file to phone", "phone", "file_transfer"),
        ("goodbye", None, None),       # wake word re-engage
        ("sleep", None, None),          # wake word re-engage
        ("hello jarvis", None, None),   # wake response
        ("what is the weather", None, None),  # unknown command
    ]

    print("=" * 60)
    print("J.A.R.V.I.S. Mk.II - Voice Intent Router Test")
    print("=" * 60)
    print()

    all_passed = True

    for phrase, exp_target, exp_cmd in test_cases:
        print(f"Speak: \"{phrase}\"")
        sent_before = len(client.sent)
        await voice.handle_voice(phrase)
        sent_after = len(client.sent)
        new_command_sent = sent_after > sent_before
        last = client.sent[-1] if client.sent else None

        # Verify
        if exp_target is None and exp_cmd is None:
            # Expected no command sent (wake/sleep/unknown)
            if not new_command_sent:
                print(f"  [PASS] No command routed (as expected)\n")
            else:
                print(f"  [FAIL] Expected no command, but got: {last}\n")
                all_passed = False
        else:
            if new_command_sent and last and last['target'] == exp_target and last['command'] == exp_cmd:
                print(f"  [PASS] Routed correctly\n")
            else:
                print(f"  [FAIL] Expected target={exp_target}, command={exp_cmd}, new_sent={new_command_sent}, last={last}\n")
                all_passed = False

    # Wake word gating test
    print("-" * 60)
    print("Wake Word Gating Test")
    print("-" * 60)
    voice.listening_for_wake = True
    await voice.handle_voice("Hey Jarvis")
    print(f"After wake word: listening_for_wake = {voice.listening_for_wake}")
    assert voice.listening_for_wake == False, "Wake word should disable listening_for_wake"
    print("[PASS] Wake word 'Hey Jarvis' acknowledged and command mode enabled\n")

    await voice.handle_voice("system status")
    print(f"After command: listening_for_wake = {voice.listening_for_wake}")
    assert voice.listening_for_wake == False, "Should stay in command mode"
    print("[PASS] Remains in command mode after command\n")

    await voice.handle_voice("goodbye")
    print(f"After goodbye: listening_for_wake = {voice.listening_for_wake}")
    assert voice.listening_for_wake == True, "Goodbye should return to wake-word standby"
    print("[PASS] 'Goodbye' returns to wake-word standby\n")

    print("=" * 60)
    if all_passed:
        print("RESULT: ALL VOICE INTENT ROUTER TESTS PASSED")
    else:
        print("RESULT: SOME TESTS FAILED")
    print("=" * 60)


asyncio.run(test_voice_router())
