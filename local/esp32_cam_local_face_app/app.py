import os, time, json, threading
from pathlib import Path
from datetime import datetime
import cv2, numpy as np
from flask import Flask, Response, request, jsonify, render_template_string, send_from_directory

ROOT=Path(__file__).resolve().parent; DATA=ROOT/'data'; FACES=DATA/'faces'; EVENTS=DATA/'events'; MODEL=DATA/'lbph.yml'; LABELS=DATA/'labels.json'
FACES.mkdir(parents=True,exist_ok=True); EVENTS.mkdir(parents=True,exist_ok=True)
URL=os.environ.get('CAMERA_URL','http://192.168.1.11/stream'); app=Flask(__name__)
lock=threading.Lock(); state={'status':'Starting','recognition':True}; latest_frame=None; latest_jpeg=None; last_alert={}
cascade=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
recognizer=cv2.face.LBPHFaceRecognizer_create(); names={}

def log_event(kind,name,score,frame):
    now=time.time(); key=kind+':'+name
    if now-last_alert.get(key,0)<30:return
    last_alert[key]=now; stamp=datetime.now().strftime('%Y%m%d_%H%M%S'); fn=f'{stamp}_{kind}.jpg'; cv2.imwrite(str(EVENTS/fn),frame)
    e={'time':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'kind':kind,'name':name,'score':round(float(score),1),'image':fn}
    p=DATA/'events.json'; events=json.loads(p.read_text()) if p.exists() else []; events.insert(0,e); p.write_text(json.dumps(events[:100],indent=2)); print('[EVENT]',e)

def worker():
 global latest_frame,latest_jpeg
 while True:
  cap=cv2.VideoCapture(URL); cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
  if not cap.isOpened(): state['status']='Cannot open ESP32 stream'; time.sleep(3); continue
  state['status']='Camera connected'
  while True:
   ok,frame=cap.read()
   if not ok: state['status']='Stream read failed; reconnecting'; break
   with lock: latest_frame=frame.copy()
   out=frame.copy(); gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY); faces=cascade.detectMultiScale(gray,1.2,5,minSize=(60,60))
   if state['recognition']:
    for x,y,w,h in faces:
     crop=cv2.resize(gray[y:y+h,x:x+w],(200,200)); name='Unknown'; score=999.; kind='unknown'
     if names:
      label,dist=recognizer.predict(crop); score=dist
      if dist<65 and label in names: name=names[label]; kind='known'
     color=(0,180,0) if kind=='known' else (0,0,255); cv2.rectangle(out,(x,y),(x+w,y+h),color,2); cv2.putText(out,f'{name} [{score:.0f}]',(x,y-8),cv2.FONT_HERSHEY_SIMPLEX,.55,color,2); log_event(kind,name,score,frame)
   ok,enc=cv2.imencode('.jpg',out,[cv2.IMWRITE_JPEG_QUALITY,80])
   if ok:
    with lock: latest_jpeg=enc.tobytes()
  cap.release(); time.sleep(1)

PAGE='''<!doctype html><meta name="viewport" content="width=device-width"><title>ESP32-CAM Face Monitor</title><style>body{font:16px system-ui;background:#111827;color:#eee;max-width:950px;margin:20px auto;padding:0 12px}section{background:#1f2937;padding:14px;margin:12px 0;border-radius:8px}img{width:100%;background:#000}button,input{padding:9px;margin:4px}</style><h1>Local ESP32-CAM Face Monitor</h1><p id="status">Connecting…</p><section><img src="/processed.mjpg"></section><section><h2>Register person</h2><input id="name" placeholder="Person name"><button onclick="capture()">Capture registration image</button><button onclick="train()">Train recognizer</button><p id="msg"></p><p>Capture 10–20 samples per person, with slight changes in angle and lighting.</p></section><section><h2>Notifications</h2><button onclick="Notification.requestPermission()">Enable browser notifications</button><p>Keep this dashboard open for browser alerts. Unknown-face events are logged with snapshots.</p></section><section><h2>Events</h2><div id="events"></div></section><script>let prev='';async function refresh(){let s=await fetch('/api/status').then(r=>r.json());status.textContent=s.status+' | Recognition '+(s.recognition?'ON':'OFF');let es=await fetch('/api/events').then(r=>r.json());events.innerHTML=es.map(e=>`<p>${e.time} — <b>${e.kind}</b>: ${e.name} <a href="/events/${e.image}" target="_blank">snapshot</a></p>`).join('');if(es.length&&es[0].time+es[0].name!==prev){prev=es[0].time+es[0].name;if(es[0].kind==='unknown'&&Notification.permission==='granted')new Notification('Unknown face detected',{body:es[0].time})}}async function capture(){let n=document.getElementById('name').value.trim();if(!n)return;let r=await fetch('/api/enroll',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n})});msg.textContent=(await r.json()).message}async function train(){let r=await fetch('/api/train',{method:'POST'});msg.textContent=(await r.json()).message}setInterval(refresh,2000);refresh();</script>'''
@app.get('/')
def home():return render_template_string(PAGE)
@app.get('/processed.mjpg')
def stream():
 def gen():
  while True:
   with lock: b=latest_jpeg
   if b: yield b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: '+str(len(b)).encode()+b'\r\n\r\n'+b+b'\r\n'
   time.sleep(.08)
 return Response(gen(),mimetype='multipart/x-mixed-replace; boundary=frame')
@app.get('/api/status')
def status():return jsonify(state)
@app.get('/api/events')
def events():
 p=DATA/'events.json'; return jsonify(json.loads(p.read_text()) if p.exists() else [])
@app.post('/api/enroll')
def enroll():
 n=(request.json or {}).get('name','').strip()
 if not n or len(n)>60:return jsonify(message='Enter a name up to 60 characters.'),400
 with lock: f=None if latest_frame is None else latest_frame.copy()
 if f is None:return jsonify(message='No camera frame yet.'),503
 g=cv2.cvtColor(f,cv2.COLOR_BGR2GRAY); faces=cascade.detectMultiScale(g,1.2,5,minSize=(60,60))
 if len(faces)!=1:return jsonify(message=f'Need exactly one face; detected {len(faces)}.'),400
 x,y,w,h=faces[0]; crop=cv2.resize(g[y:y+h,x:x+w],(200,200)); d=FACES/n; d.mkdir(parents=True,exist_ok=True); cv2.imwrite(str(d/f'{int(time.time()*1000)}.png'),crop)
 return jsonify(message=f'Sample saved for {n}. Capture 10–20 samples, then train.')
@app.post('/api/train')
def train():
 imgs=[]; labs=[]; mapping={}
 for idx,d in enumerate(sorted(x for x in FACES.iterdir() if x.is_dir())):
  fs=list(d.glob('*.png'))
  if fs:mapping[idx]=d.name
  for p in fs:
   im=cv2.imread(str(p),0)
   if im is not None:imgs.append(cv2.resize(im,(200,200)));labs.append(idx)
 if len(imgs)<2:return jsonify(message='Capture at least two samples first.'),400
 recognizer.train(imgs,np.array(labs,dtype=np.int32));recognizer.write(str(MODEL));LABELS.write_text(json.dumps(mapping));names.update(mapping)
 return jsonify(message=f'Trained {len(imgs)} samples for {len(mapping)} people.')
@app.route('/events/<path:filename>')
def event_image(filename):return send_from_directory(EVENTS,filename)
if __name__=='__main__':
 if MODEL.exists() and LABELS.exists():
  recognizer.read(str(MODEL));names.update({int(k):v for k,v in json.loads(LABELS.read_text()).items()})
 threading.Thread(target=worker,daemon=True).start();app.run(host='0.0.0.0',port=5000,threaded=True)
