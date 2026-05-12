#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <DNSServer.h>
#include <Servo.h>

// ── L298N Motor Pins ──────────────────────────────────────────────
#define IN1 D1   // Left Motor Forward
#define IN2 D2   // Left Motor Backward
#define IN3 D3   // Right Motor Forward
#define IN4 D4   // Right Motor Backward

// ── Servo Pins ────────────────────────────────────────────────────
#define SERVO1_PIN D6
#define SERVO2_PIN D7

// ── Captive Portal Setup ──────────────────────────────────────────
const char* AP_SSID = "ESP8266-Car";
const char* AP_PASS = "";            // Open network (no password)

ESP8266WebServer server(80);
DNSServer dnsServer;

Servo servo1;
Servo servo2;

int servo1Angle = 90;
int servo2Angle = 90;

// ── HTML Page (served as captive portal) ─────────────────────────
const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no"/>
<title>ESP Car Control</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Rajdhani:wght@400;600&display=swap');

  :root{
    --bg:#0a0c10;
    --panel:#11151c;
    --border:#1e2a3a;
    --accent:#00e5ff;
    --accent2:#ff3d71;
    --btn:#151d28;
    --btnhov:#1e2d40;
    --text:#c8daea;
    --dim:#4a6070;
  }

  *{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent;}
  body{background:var(--bg);font-family:'Rajdhani',sans-serif;color:var(--text);
       min-height:100vh;display:flex;flex-direction:column;align-items:center;
       padding:16px 12px;gap:14px;}

  h1{font-family:'Orbitron',sans-serif;font-size:1.3rem;letter-spacing:4px;
     color:var(--accent);text-transform:uppercase;
     text-shadow:0 0 20px rgba(0,229,255,.4);margin-top:6px;}

  .badge{font-size:.65rem;letter-spacing:2px;color:var(--dim);text-transform:uppercase;}

  /* STATUS */
  #status{background:var(--panel);border:1px solid var(--border);border-radius:10px;
          padding:8px 20px;font-size:.85rem;letter-spacing:1px;color:var(--accent);
          min-width:180px;text-align:center;transition:color .3s;}

  /* DPAD */
  .dpad{display:grid;grid-template-columns:repeat(3,70px);grid-template-rows:repeat(3,70px);gap:6px;}
  .dpad-cell{display:flex;align-items:center;justify-content:center;}

  .btn{width:70px;height:70px;border-radius:12px;border:1px solid var(--border);
       background:var(--btn);cursor:pointer;font-size:1.6rem;
       color:var(--text);display:flex;align-items:center;justify-content:center;
       transition:background .15s,transform .1s,box-shadow .15s;
       user-select:none;-webkit-user-select:none;}
  .btn:active,.btn.active{background:var(--btnhov);transform:scale(.92);
    box-shadow:0 0 18px rgba(0,229,255,.3);}

  .stop-btn{width:70px;height:70px;border-radius:12px;background:#1a0a10;
            border:1px solid #3d1020;cursor:pointer;font-size:1rem;font-weight:700;
            font-family:'Orbitron',sans-serif;color:var(--accent2);
            letter-spacing:1px;transition:background .15s,box-shadow .15s;
            user-select:none;-webkit-user-select:none;}
  .stop-btn:active{background:#2a0f1a;box-shadow:0 0 18px rgba(255,61,113,.4);}

  /* SERVO PANEL */
  .servo-panel{background:var(--panel);border:1px solid var(--border);border-radius:14px;
               padding:16px 20px;width:100%;max-width:360px;display:flex;flex-direction:column;gap:14px;}
  .servo-row{display:flex;flex-direction:column;gap:6px;}
  .servo-label{font-size:.8rem;letter-spacing:2px;text-transform:uppercase;color:var(--dim);
               display:flex;justify-content:space-between;}
  .servo-label span{color:var(--accent);font-weight:700;}

  input[type=range]{-webkit-appearance:none;width:100%;height:6px;border-radius:3px;
    background:linear-gradient(to right,var(--accent) 0%,var(--accent) var(--pct,50%),var(--border) var(--pct,50%),var(--border) 100%);}
  input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:20px;height:20px;
    border-radius:50%;background:var(--accent);cursor:pointer;box-shadow:0 0 10px rgba(0,229,255,.5);}

  /* BOTTOM GLOW LINE */
  .line{width:60%;height:1px;background:linear-gradient(to right,transparent,var(--accent),transparent);opacity:.3;}
</style>
</head>
<body>

<h1>&#9654; ESP Car</h1>
<div class="badge">Captive Portal · L298N + Servo</div>

<div id="status">READY</div>

<!-- D-Pad -->
<div class="dpad">
  <div class="dpad-cell"></div>
  <div class="dpad-cell">
    <button class="btn" id="btnF" ontouchstart="go('F')" ontouchend="go('S')" onmousedown="go('F')" onmouseup="go('S')">▲</button>
  </div>
  <div class="dpad-cell"></div>

  <div class="dpad-cell">
    <button class="btn" id="btnL" ontouchstart="go('L')" ontouchend="go('S')" onmousedown="go('L')" onmouseup="go('S')">◀</button>
  </div>
  <div class="dpad-cell">
    <button class="stop-btn" onclick="go('S')">STOP</button>
  </div>
  <div class="dpad-cell">
    <button class="btn" id="btnR" ontouchstart="go('R')" ontouchend="go('S')" onmousedown="go('R')" onmouseup="go('S')">▶</button>
  </div>

  <div class="dpad-cell"></div>
  <div class="dpad-cell">
    <button class="btn" id="btnB" ontouchstart="go('B')" ontouchend="go('S')" onmousedown="go('B')" onmouseup="go('S')">▼</button>
  </div>
  <div class="dpad-cell"></div>
</div>

<!-- Servo Sliders -->
<div class="servo-panel">
  <div class="servo-row">
    <div class="servo-label">Servo 1 (D6) <span id="s1val">90°</span></div>
    <input type="range" id="s1" min="0" max="180" value="90"
           oninput="moveServo(1,this.value)" onchange="moveServo(1,this.value)"/>
  </div>
  <div class="servo-row">
    <div class="servo-label">Servo 2 (D7) <span id="s2val">90°</span></div>
    <input type="range" id="s2" min="0" max="180" value="90"
           oninput="moveServo(2,this.value)" onchange="moveServo(2,this.value)"/>
  </div>
</div>

<div class="line"></div>

<script>
  // Update slider gradient fill
  document.querySelectorAll('input[type=range]').forEach(r=>{
    r.style.setProperty('--pct', r.value/180*100+'%');
    r.addEventListener('input',()=>r.style.setProperty('--pct',r.value/180*100+'%'));
  });

  function setStatus(msg,color='var(--accent)'){
    const el=document.getElementById('status');
    el.textContent=msg; el.style.color=color;
  }

  async function go(dir){
    const labels={F:'FORWARD',B:'BACKWARD',L:'LEFT',R:'RIGHT',S:'STOP'};
    const colors={F:'var(--accent)',B:'var(--accent)',L:'var(--accent)',R:'var(--accent)',S:'var(--accent2)'};
    setStatus(labels[dir]||dir, colors[dir]||'var(--accent)');
    try{ await fetch('/motor?dir='+dir); }catch(e){ setStatus('ERR','#ff6b35'); }
  }

  let servoTimer=[null,null];
  function moveServo(id,val){
    document.getElementById('s'+id+'val').textContent=val+'°';
    clearTimeout(servoTimer[id-1]);
    servoTimer[id-1]=setTimeout(()=>{
      fetch('/servo?id='+id+'&angle='+val).catch(()=>{});
    },60);
  }
</script>
</body>
</html>
)rawliteral";

// ── Motor Control ─────────────────────────────────────────────────
void motorStop(){
  digitalWrite(IN1,LOW); digitalWrite(IN2,LOW);
  digitalWrite(IN3,LOW); digitalWrite(IN4,LOW);
}
void motorForward(){
  digitalWrite(IN1,HIGH); digitalWrite(IN2,LOW);
  digitalWrite(IN3,HIGH); digitalWrite(IN4,LOW);
}
void motorBackward(){
  digitalWrite(IN1,LOW); digitalWrite(IN2,HIGH);
  digitalWrite(IN3,LOW); digitalWrite(IN4,HIGH);
}
void motorLeft(){
  digitalWrite(IN1,LOW);  digitalWrite(IN2,HIGH);
  digitalWrite(IN3,HIGH); digitalWrite(IN4,LOW);
}
void motorRight(){
  digitalWrite(IN1,HIGH); digitalWrite(IN2,LOW);
  digitalWrite(IN3,LOW);  digitalWrite(IN4,HIGH);
}

// ── HTTP Handlers ─────────────────────────────────────────────────
void handleRoot(){
  server.send_P(200,"text/html",INDEX_HTML);
}

void handleMotor(){
  if(server.hasArg("dir")){
    String dir = server.arg("dir");
    if(dir=="F") motorForward();
    else if(dir=="B") motorBackward();
    else if(dir=="L") motorLeft();
    else if(dir=="R") motorRight();
    else              motorStop();
  }
  server.send(200,"text/plain","OK");
}

void handleServo(){
  if(server.hasArg("id") && server.hasArg("angle")){
    int id    = server.arg("id").toInt();
    int angle = constrain(server.arg("angle").toInt(), 0, 180);
    if(id==1){ servo1.write(angle); servo1Angle=angle; }
    else      { servo2.write(angle); servo2Angle=angle; }
  }
  server.send(200,"text/plain","OK");
}

// Captive portal redirect — redirect everything unknown to root
void handleCaptive(){
  server.sendHeader("Location","http://192.168.4.1/",true);
  server.send(302,"text/plain","");
}

// ── Setup ─────────────────────────────────────────────────────────
void setup(){
  Serial.begin(115200);

  // Motor pins
  pinMode(IN1,OUTPUT); pinMode(IN2,OUTPUT);
  pinMode(IN3,OUTPUT); pinMode(IN4,OUTPUT);
  motorStop();

  // Servos
  servo1.attach(D6); servo1.write(90);
  servo2.attach(D7); servo2.write(90);

  // Access Point
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASS);
  Serial.print("AP IP: ");
  Serial.println(WiFi.softAPIP());   // Usually 192.168.4.1

  // DNS — redirect all domains to us (captive portal trick)
  dnsServer.start(53,"*",WiFi.softAPIP());

  // Routes
  server.on("/",        handleRoot);
  server.on("/motor",   handleMotor);
  server.on("/servo",   handleServo);
  server.on("/generate_204",     handleCaptive);  // Android captive check
  server.on("/hotspot-detect.html", handleCaptive); // iOS/macOS captive check
  server.on("/connecttest.txt",  handleCaptive);
  server.onNotFound(handleCaptive);

  server.begin();
  Serial.println("Server started");
}

// ── Loop ──────────────────────────────────────────────────────────
void loop(){
  dnsServer.processNextRequest();
  server.handleClient();
}
