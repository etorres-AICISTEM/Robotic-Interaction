import speech_recognition as sr
mics = sr.Microphone.list_microphone_names()

for index, name in enumerate(mics):
    print(f"Microphone with index {index}: {name}")