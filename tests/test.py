import requests
import json

url = "http://180.153.21.76:12119/custom_audio_to_text?spilit_time=10"
headers = {"accept": "application/json"}

def stream_json_objects(response):
    decoder = json.JSONDecoder()
    buffer = ""
    for chunk in response.iter_content(chunk_size=1024):
        if not chunk:
            continue
        buffer += chunk.decode("utf-8", errors="ignore")
        while True:
            stripped = buffer.lstrip()
            if not stripped:
                buffer = ""
                break
            try:
                obj, idx = decoder.raw_decode(stripped)
                yield obj
                # Advance buffer by the consumed part (including any leading spaces we stripped)
                consumed = len(buffer) - len(stripped) + idx
                buffer = buffer[consumed:]
            except json.JSONDecodeError:
                # Need more data
                break


file_path = 'C:\\Users\\CHENQIMING\\Desktop\\工作数据\\测试文件\\vad_example.wav'
with open(file_path, "rb") as f:
    files = {"file": ("vad_example.wav", f, "audio/wav")}
    response = requests.post(url, headers=headers, files=files, stream=True)

print(response)

if response.status_code != 200:
    print("HTTP Error:", response.status_code)
else:
    try:
        for obj in stream_json_objects(response):
            if isinstance(obj, dict) and "text" in obj:
                print(obj["text"], end="", flush=True)
            else:
                print(obj, flush=True)
    finally:
        # Ensure the response is closed
        response.close()
