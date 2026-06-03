import http.client, mimetypes, json, os
CRLF='\r\n'
boundary='----Boundary1234567890'
file_path=r'C:\Users\rishi\Downloads\temple-poinTR-main\temple-poinTR-main\Frontend_3dita\frontend\public\mock\sample_before.ply'
fields={'model':'geometry_only','params':json.dumps({'enable_hole_detection':True,'force_completion':True,'enable_trimesh_repair':True,'central_void_min_ratio':0.05,'central_void_cap_segments':64})}
with open(file_path,'rb') as f:
    file_data=f.read()
filename=os.path.basename(file_path)
    
body=bytearray()
for name,value in fields.items():
    body.extend(('--'+boundary).encode()+b'\r\n')
    body.extend(f'Content-Disposition: form-data; name="{name}"'.encode()+b'\r\n\r\n')
    body.extend(str(value).encode()+b'\r\n')

body.extend(('--'+boundary).encode()+b'\r\n')
body.extend(f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode()+b'\r\n')
ctype=mimetypes.guess_type(filename)[0] or 'application/octet-stream'
body.extend(f'Content-Type: {ctype}'.encode()+b'\r\n\r\n')
body.extend(file_data+b'\r\n')
body.extend(('--'+boundary+'--\r\n').encode())

conn=http.client.HTTPConnection('localhost',8010, timeout=120)
headers={'Content-Type':f'multipart/form-data; boundary={boundary}'}
conn.request('POST','/api/reconstruct', body, headers)
res=conn.getresponse()
data=res.read().decode()
print('STATUS',res.status)
print(data)
