import pyaudio
import sys

p = pyaudio.PyAudio()

print("Available audio devices:\n")
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    print(f"Device {i}: {info['name']}")
    print(f"  Channels: {info['maxInputChannels']}")
    print(f"  Sample Rate: {info['defaultSampleRate']} Hz")
    print(f"  Default Input: {info['maxInputChannels'] > 0}")
    print()

# Check which sample rates work for device 24
print("\nTesting device 24 with different sample rates:")
device_index = 24
test_rates = [8000, 11025, 16000, 22050, 44100, 48000]

for rate in test_rates:
    try:
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=4096
        )
        stream.stop_stream()
        stream.close()
        print(f"✓ {rate} Hz: SUPPORTED")
    except OSError as e:
        print(f"✗ {rate} Hz: NOT SUPPORTED")

p.terminate()
