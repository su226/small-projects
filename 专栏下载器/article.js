let appbar = document.getElementById("appbar");
let title = document.getElementById("title");
let banner = document.getElementById("banner");
function blend(r, a, b) {
  return b * r + a * (1 - r);
}
function move() {
  let r = Math.min(1, document.documentElement.scrollTop / 192);
  appbar.style.height = `${blend(r, 256, 64)}px`;
  title.style.fontSize = `${blend(r, 32, 16)}px`;
  title.style.bottom = `${blend(r, 16, 0)}px`;
  banner.style.opacity = `${1 - r}`;
  appbar.toggleAttribute("shadow", r == 1)
}
window.onscroll = move;
move();