import urllib.request
import uuid

boundary = '----WebKitFormBoundary' + uuid.uuid4().hex
body = []
body.append(b'--' + boundary.encode())
body.append(b'Content-Disposition: form-data; name="file"; filename="test.ply"')
body.append(b'Content-Type: application/octet-stream')
body.append(b'')
body.append(b"""ply
format ascii 1.0
element vertex 3
property float x
property float y
property float z
end_header
0 0 0
1 0 0
0 1 0
""")
body.append(b'--' + boundary.encode())
body.append(b'Content-Disposition: form-data; name="model"')
body.append(b'')
body.append(b'ae')
body.append(b'--' + boundary.encode())
body.append(b'Content-Disposition: form-data; name="params"')
body.append(b'')
body.append(b'{}')
body.append(b'--' + boundary.encode() + b'--')
body.append(b'')
body_bytes = b'\r\n'.join(body)
req = urllib.request.Request('http://localhost:8000/api/reconstruct', data=body_bytes)
req.add_header('Content-Type', 'multipart/form-data; boundary=%s' % boundary)
with urllib.request.urlopen(req) as resp:
    print('post', resp.status, resp.read().decode())
