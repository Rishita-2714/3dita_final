import urllib.request
import urllib.parse
import json

url = 'https://api.infinitescript.com/gateway/file?name=GRNet-ShapeNet.pth'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://gateway.infinitescript.com',
    'Referer': 'https://gateway.infinitescript.com/'
}

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        print("Status Code:", response.getcode())
        data = json.loads(response.read().decode('utf-8'))
        print("Data received:")
        print(json.dumps(data, indent=2))
except Exception as e:
    print("Error:", e)
