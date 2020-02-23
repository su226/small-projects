let audio = new Audio("door.mp3");
let audioCtx = new AudioContext();
let analyser = audioCtx.createAnalyser();
let source = audioCtx.createMediaElementSource(audio);
const size = analyser.fftSize;
let tData = new Uint8Array(size);
let fData = new Uint8Array(size);
source.connect(analyser);
analyser.connect(audioCtx.destination);

audio.controls = true;
audio.id = "audio";
document.body.appendChild(audio);

let canvas = document.getElementById("canvas");
let ctx = canvas.getContext("2d");

let W;
let H;
let X;
let Y;
window.addEventListener("resize", function resize() {
  W = canvas.width = document.documentElement.clientWidth;
  H = canvas.height = document.documentElement.clientHeight;
  X = W / 2;
  Y = H / 2;
  ctx.fillStyle = ctx.strokeStyle = "#fff";
  ctx.lineWidth = 8;
  return resize;
}());

const RADIUS_TRIANGLE = 192;
const RADIUS_FREQUENCY = 96;
const DIVISOR = 262144;
const MIN_SCALE = 1;
const FREQUENCY_COUNT = 32;
const FREQUENCY_INCREACEMENT = 16;
const FREQUENCY_MAX = FREQUENCY_COUNT * FREQUENCY_INCREACEMENT;
const FREQUENCY_COUNT_REVERSE = 1 / FREQUENCY_COUNT;
const ANGLE_MULTIPLIER = 0.2;

let m = 1;
function draw() {
  const r = RADIUS_TRIANGLE * m;
  const r2 = RADIUS_FREQUENCY * m;
  const a = audio.currentTime * ANGLE_MULTIPLIER;
  const c1 = Math.cos(a - 1.57);
  const s1 = Math.sin(a - 1.57);
  const c2 = Math.cos(a + 0.52);
  const s2 = Math.sin(a + 0.52);
  const c3 = Math.cos(a + 2.62);
  const s3 = Math.sin(a + 2.62);
  const x1 = X + r * c1;
  const y1 = Y + r * s1;
  const x2 = X + r * c2;
  const y2 = Y + r * s2;
  const x3 = X + r * c3;
  const y3 = Y + r * s3;
  const rp = r * audio.currentTime / audio.duration;
  const x1a = X + rp * c1;
  const y1a = Y + rp * s1;
  const x2a = X + rp * c2;
  const y2a = Y + rp * s2;
  const x3a = X + rp * c3;
  const y3a = Y + rp * s3;
  ctx.clearRect(0, 0, W, H);

  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.lineTo(x3, y3);
  ctx.closePath();
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(x1a, y1a);
  ctx.lineTo(x2a, y2a);
  ctx.lineTo(x3a, y3a);
  ctx.fill();

  function drawFreq(xa, ya, xb, yb, a) {
    ctx.beginPath();
    let p = 0;
    const c = Math.cos(a);
    const s = Math.sin(a);
    for (let i = 0; i <= FREQUENCY_MAX; i += FREQUENCY_INCREACEMENT) {
      const r3 = r2 * fData[i] / 256;
      const xs = xa * (1 - p) + xb * p;
      const ys = ya * (1 - p) + yb * p;
      const xt = xs + r3 * c;
      const yt = ys + r3 * s;
      ctx.moveTo(xs, ys);
      ctx.lineTo(xt, yt);
      p += FREQUENCY_COUNT_REVERSE;
    }
    ctx.stroke();
  }
  drawFreq(x1, y1, x2, y2, a - 0.52);
  drawFreq(x2, y2, x3, y3, a + 1.57);
  drawFreq(x3, y3, x1, y1, a + 3.67);
}

function update() {
  if (audio.seeking) {
    draw();
  } else if (audio.paused) {
  } else {
    analyser.getByteTimeDomainData(tData);
    analyser.getByteFrequencyData(fData);
    m = 0;
    tData.forEach(i => { m += Math.abs(i - 128) });
    m = (m / DIVISOR + MIN_SCALE);
    draw();
  }
  requestAnimationFrame(update);
}
requestAnimationFrame(update);

function resize() {
  W = canvas.width = document.documentElement.clientWidth;
  H = canvas.height = document.documentElement.clientHeight;
  X = W / 2;
  Y = H / 2;
  ctx.fillStyle = ctx.strokeStyle = "#fff";
  ctx.lineWidth = 8;
  draw();
}

let clock = setInterval(() => {
  if (!isNaN(audio.duration)) {
    resize();
    window.addEventListener("resize", resize);
    clearInterval(clock);
  }
}, 100);

// document.addEventListener("click", function play() {
//   audio.play();
//   document.removeEventListener("click", play);
// });