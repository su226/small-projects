// ==UserScript==
// @name           贴吧自动签到
// @namespace      https://su226.github.io
// @author         congxz6688, su226
// @description    基于tiebaAllSign用户脚本修改
// @include        http*://www.baidu.com/*
// @include        http*://tieba.baidu.com/*
// @connect        tieba.baidu.com
// @icon           data:image/webp;base64,UklGRlYCAABXRUJQVlA4TEoCAAAvP8APEM/EIJKkRo0MjGOXD5ckiAVTPJXuBAJJovsDLMA2kiQ1zyyXc1D+kchXDMyjsG3bpnuXeQPiNADAoiChgkQNjYQBASMKalT7APjxAwDe9SL/itdSEeJLvyBDAhQvDvx/fsXJhwVT9A+CKCIqSBe3mAMhzmILINu2bUOSdrVt27Zt27aVtuLGDrTt/t48J+pm3Nd+iOj/BMDmiD5xFJz9z8ZgmyOl0YNtDkpUuNk10OYAacBAm0OTFCdHlwD0pTxJaQoZXXGoNI0k42vOlKdTjG84UplBOTjpRnUW5eCEP9bmOGn8WJtDuqpzKAfHfFgdIY2C7dpcysERHy7U5lMODvtwob6A6kEDF+qLqB4wcKGxhOo+AxcaS6nuMXChuYzqLgMXmsup7vTgQmsF1e0eXGitorrNgwvtNVS3dOBCex3VTR240F5PdUMH1l/3orOB6vo2rJtDp+x1NlJd24Z1/zDD07Y6m6mubsG6fzQgwzN2vK1UV7Zg3T8ekGR4xoa3neryFuxfDCiGZ/vn7aC6rIkeZv5IDM8Bw8aIw7u8XVSXNtDTV78lRueR2OymuqSBHr/8JTG6kMTspbqojp6/+CkxuqiZ/VQX1JHC5z8kRpclc4DqvBpS+ey7xPhqlzlIdU4VKX36TWJ8DfAPBcrsKlL75KvE+Lp/JKA8s4IUP/4iMV4cUJ5eRqoffZYSTisj5Q8/9WNqCal/8DHR5CIcvP8hwaQCnLz3XpmYh6N33wkTcnD2zluS/3Jw+PYb/s3C6VsLM0gp
// @updateURL      https://cdn.jsdelivr.net/gh/su226/small-projects/贴吧自动签到/贴吧自动签到.user.js
// @grant          GM_getValue
// @grant          GM_setValue
// @grant          GM_xmlhttpRequest
// @version        1.0.0+20201011
// ==/UserScript==

/** 脚本版本 */
const VERSION = "1.0.0+20201011";

/** 签到的图标，来自Material Design Icons */
const SIGN_ICON = `<svg sign-icon viewBox="0 0 24 24"><path d="M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z" /></svg>`;

/** 设置的图标，来自Material Design Icons */
const SETTINGS_ICON = `<svg sign-icon viewBox="0 0 24 24"><path d="M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.34 19.43,11L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.5,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.5,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.21,8.95 2.27,9.22 2.46,9.37L4.57,11C4.53,11.34 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.21,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.03 4.95,18.95L7.44,17.94C7.96,18.34 8.5,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.5,18.67 16.04,18.34 16.56,17.94L19.05,18.95C19.27,19.03 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z" /></svg>`;

/** 关闭的图标，来自Material Design Icons */
const CLOSE_ICON = `<svg sign-icon viewBox="0 0 24 24"><path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z" /></svg>`;

/** 最小化的图标，来自Material Design Icons */
const MINIMIZE_ICON = `<svg sign-icon viewBox="0 0 24 24"><path d="M19,13H5V11H19V13Z" /></svg>`;

document.body.insertBefore(document.createElement("style"), document.body.firstChild).textContent = `\
/* 签到浮窗 */

#sign-widget {
  display: flex;
  position: fixed;
  padding-top: 8px;
  z-index: 10006;
  border-radius: 4px;
  background-color: #333;
  color: #fff;
  font-family: sans-serif;
  font-size: 16px;
  line-height: 1.2;
  white-space: nowrap;
  box-shadow: /* 4dp */
    0px 2px 4px -1px rgba(0,0,0,.2),
    0px 4px 5px 0px rgba(0,0,0,.14),
    0px 1px 10px 0px rgba(0,0,0,.12);
}

/* 签到浮窗拖动区 */

#sign-drag {
  position: absolute;
  left: 2px;
  top: 2px;
  right: 2px;
  height: 0;
  display: block;
  border-top: 4px dotted rgba(255,255,255,.2);
}

[dragging] {
  user-select: none;
}

/* 签到浮窗控件 */

#sign-control {
  display: flex;
}

/* (伪) Material Design 风格按钮 */

[sign-icon] {
  width: 24px;
  height: 24px;
  fill: currentColor;
}

[sign-btn] {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: 0;
  padding: 0;
  background: none;
  color: #fff;
  cursor: pointer;
  border-radius: 50%;
  transition: .25s;
}

[sign-btn]:hover {
  background-color: rgba(255,255,255,.2);
}

[sign-btn]:active{
  background-color: rgba(255,255,255,.4);
}

#sign-check {
  display: none;
}

#sign-check-label {
  color: #ff4336;
}

#sign-check:checked + #sign-check-label {
  color: #4caf50;
}

/* 签到浮窗信息 */

#sign-message {
  padding: 8px 12px;
  display: table-cell;
  vertical-align: middle;
}

/* 签到浮窗隐藏控件 */

[show="control"] #sign-message,
[show="message"] #sign-control {
  display: none
}

#sign-widget[show="none"] {
  display: none;
}

/* 签到模态框 */

#sign-modal {
  position: fixed;
  right: 0;
  top: 0;
  height: 100%;
  z-index: 10007;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  text-align: left;
  color: #fff;
  background-color: #424242;
  font-family: sans-serif;
  font-size: 16px;
  line-height: 1.2;
  box-shadow: /* 16dp */
    0px 8px 10px -5px rgba(0,0,0,.2),
    0px 16px 24px 2px rgba(0,0,0,.14),
    0px 6px 30px 5px rgba(0,0,0,.12);
}

#sign-widget div,
#sign-modal div,
#sign-modal p {
  font-size: inherit;
}

#sign-modal[hide] {
  display: none;
}

/* 签到模态框关闭按钮 */

#sign-modal-close {
  position: fixed;
  right: 4px;
  top: 4px;
}

#sign-modal-minimize {
  position: fixed;
  right: 44px;
  top: 4px;
}

/* 签到模态框头 */
#sign-modal-header {
  top: 0;
  left: 0;
  padding-top: 16px;
  padding-left: 16px;
  width: 100%;
  height: 32px;
  flex-shrink: 0;
}

/* 签到浮窗表格 */

#sign-modal-wrap {
  overflow-x: hidden;
}

#sign-modal table {
  white-space: nowrap;
  border-collapse: collapse;
}

#sign-modal tr {
  border-bottom: 1px solid #515151;
  border-top: 1px solid #515151;
}

#sign-modal th,
#sign-modal td {
  padding: 6px 0 6px 16px;
  font-family: inherit;
  font-size: inherit;
  line-height: inherit;
}

#sign-modal th:last-child,
#sign-modal td:last-child {
  padding-right: 16px;
}

#sign-modal th {
  text-align: center;
}

/* 签到浮窗链接 */
#sign-modal a,
#sign-modal a:active,
#sign-modal a:visited,
#sign-message a {
  text-decoration: none;
  color: #90caf9;
}

#sign-modal a:hover,
#sign-message a:hover {
  text-decoration: underline;
}

/* 设置浮窗 */
#sign-settings-wrap {
  padding-right: 44px;
}

#sign-settings-wrap p,
#sign-settings-wrap li {
  margin: 8px;
}

#sign-blacklist-edit,
#sign-interval-edit {
  width: 160px;
  color: initial;
}

[sign-pos] {
  margin: 0;
}`;

// clang-format off
// md5.js精简版 http://pajhome.org.uk/crypt/md5/md5.html
let hex_md5 = (() => { function rstr_md5(s) { return binl2rstr(binl_md5(rstr2binl(s), s.length * 8)); } function rstr2hex(input) { let hex_tab = "0123456789abcdef"; let output = ""; let x; for (let i = 0; i < input.length; i++) { x = input.charCodeAt(i); output += hex_tab.charAt((x >>> 4) & 0x0F) + hex_tab.charAt(x & 0x0F); } return output; } function str2rstr_utf8(input) { let output = ""; let i = -1; let x, y; while (++i < input.length) { x = input.charCodeAt(i); y = i + 1 < input.length ? input.charCodeAt(i + 1) : 0; if (0xD800 <= x && x <= 0xDBFF && 0xDC00 <= y && y <= 0xDFFF) { x = 0x10000 + ((x & 0x03FF) << 10) + (y & 0x03FF); i++; } if (x <= 0x7F) output += String.fromCharCode(x); else if (x <= 0x7FF) output += String.fromCharCode(0xC0 | ((x >>> 6) & 0x1F), 0x80 | (x & 0x3F)); else if (x <= 0xFFFF) output += String.fromCharCode(0xE0 | ((x >>> 12) & 0x0F), 0x80 | ((x >>> 6) & 0x3F), 0x80 | (x & 0x3F)); else if (x <= 0x1FFFFF) output += String.fromCharCode(0xF0 | ((x >>> 18) & 0x07), 0x80 | ((x >>> 12) & 0x3F), 0x80 | ((x >>> 6) & 0x3F), 0x80 | (x & 0x3F)); } return output; } function rstr2binl(input) { let output = Array(input.length >> 2); for (let i = 0; i < output.length; i++)output[i] = 0; for (let i = 0; i < input.length * 8; i += 8)output[i >> 5] |= (input.charCodeAt(i / 8) & 0xFF) << (i % 32); return output; } function binl2rstr(input) { let output = ""; for (let i = 0; i < input.length * 32; i += 8)output += String.fromCharCode((input[i >> 5] >>> (i % 32)) & 0xFF); return output; } function binl_md5(x, len) { x[len >> 5] |= 0x80 << ((len) % 32); x[(((len + 64) >>> 9) << 4) + 14] = len; let a = 1732584193; let b = -271733879; let c = -1732584194; let d = 271733878; for (let i = 0; i < x.length; i += 16) { let olda = a; let oldb = b; let oldc = c; let oldd = d; a = md5_ff(a, b, c, d, x[i + 0], 7, -680876936); d = md5_ff(d, a, b, c, x[i + 1], 12, -389564586); c = md5_ff(c, d, a, b, x[i + 2], 17, 606105819); b = md5_ff(b, c, d, a, x[i + 3], 22, -1044525330); a = md5_ff(a, b, c, d, x[i + 4], 7, -176418897); d = md5_ff(d, a, b, c, x[i + 5], 12, 1200080426); c = md5_ff(c, d, a, b, x[i + 6], 17, -1473231341); b = md5_ff(b, c, d, a, x[i + 7], 22, -45705983); a = md5_ff(a, b, c, d, x[i + 8], 7, 1770035416); d = md5_ff(d, a, b, c, x[i + 9], 12, -1958414417); c = md5_ff(c, d, a, b, x[i + 10], 17, -42063); b = md5_ff(b, c, d, a, x[i + 11], 22, -1990404162); a = md5_ff(a, b, c, d, x[i + 12], 7, 1804603682); d = md5_ff(d, a, b, c, x[i + 13], 12, -40341101); c = md5_ff(c, d, a, b, x[i + 14], 17, -1502002290); b = md5_ff(b, c, d, a, x[i + 15], 22, 1236535329); a = md5_gg(a, b, c, d, x[i + 1], 5, -165796510); d = md5_gg(d, a, b, c, x[i + 6], 9, -1069501632); c = md5_gg(c, d, a, b, x[i + 11], 14, 643717713); b = md5_gg(b, c, d, a, x[i + 0], 20, -373897302); a = md5_gg(a, b, c, d, x[i + 5], 5, -701558691); d = md5_gg(d, a, b, c, x[i + 10], 9, 38016083); c = md5_gg(c, d, a, b, x[i + 15], 14, -660478335); b = md5_gg(b, c, d, a, x[i + 4], 20, -405537848); a = md5_gg(a, b, c, d, x[i + 9], 5, 568446438); d = md5_gg(d, a, b, c, x[i + 14], 9, -1019803690); c = md5_gg(c, d, a, b, x[i + 3], 14, -187363961); b = md5_gg(b, c, d, a, x[i + 8], 20, 1163531501); a = md5_gg(a, b, c, d, x[i + 13], 5, -1444681467); d = md5_gg(d, a, b, c, x[i + 2], 9, -51403784); c = md5_gg(c, d, a, b, x[i + 7], 14, 1735328473); b = md5_gg(b, c, d, a, x[i + 12], 20, -1926607734); a = md5_hh(a, b, c, d, x[i + 5], 4, -378558); d = md5_hh(d, a, b, c, x[i + 8], 11, -2022574463); c = md5_hh(c, d, a, b, x[i + 11], 16, 1839030562); b = md5_hh(b, c, d, a, x[i + 14], 23, -35309556); a = md5_hh(a, b, c, d, x[i + 1], 4, -1530992060); d = md5_hh(d, a, b, c, x[i + 4], 11, 1272893353); c = md5_hh(c, d, a, b, x[i + 7], 16, -155497632); b = md5_hh(b, c, d, a, x[i + 10], 23, -1094730640); a = md5_hh(a, b, c, d, x[i + 13], 4, 681279174); d = md5_hh(d, a, b, c, x[i + 0], 11, -358537222); c = md5_hh(c, d, a, b, x[i + 3], 16, -722521979); b = md5_hh(b, c, d, a, x[i + 6], 23, 76029189); a = md5_hh(a, b, c, d, x[i + 9], 4, -640364487); d = md5_hh(d, a, b, c, x[i + 12], 11, -421815835); c = md5_hh(c, d, a, b, x[i + 15], 16, 530742520); b = md5_hh(b, c, d, a, x[i + 2], 23, -995338651); a = md5_ii(a, b, c, d, x[i + 0], 6, -198630844); d = md5_ii(d, a, b, c, x[i + 7], 10, 1126891415); c = md5_ii(c, d, a, b, x[i + 14], 15, -1416354905); b = md5_ii(b, c, d, a, x[i + 5], 21, -57434055); a = md5_ii(a, b, c, d, x[i + 12], 6, 1700485571); d = md5_ii(d, a, b, c, x[i + 3], 10, -1894986606); c = md5_ii(c, d, a, b, x[i + 10], 15, -1051523); b = md5_ii(b, c, d, a, x[i + 1], 21, -2054922799); a = md5_ii(a, b, c, d, x[i + 8], 6, 1873313359); d = md5_ii(d, a, b, c, x[i + 15], 10, -30611744); c = md5_ii(c, d, a, b, x[i + 6], 15, -1560198380); b = md5_ii(b, c, d, a, x[i + 13], 21, 1309151649); a = md5_ii(a, b, c, d, x[i + 4], 6, -145523070); d = md5_ii(d, a, b, c, x[i + 11], 10, -1120210379); c = md5_ii(c, d, a, b, x[i + 2], 15, 718787259); b = md5_ii(b, c, d, a, x[i + 9], 21, -343485551); a = safe_add(a, olda); b = safe_add(b, oldb); c = safe_add(c, oldc); d = safe_add(d, oldd); } return Array(a, b, c, d); } function md5_cmn(q, a, b, x, s, t) { return safe_add(bit_rol(safe_add(safe_add(a, q), safe_add(x, t)), s), b); } function md5_ff(a, b, c, d, x, s, t) { return md5_cmn((b & c) | ((~b) & d), a, b, x, s, t); } function md5_gg(a, b, c, d, x, s, t) { return md5_cmn((b & d) | (c & (~d)), a, b, x, s, t); } function md5_hh(a, b, c, d, x, s, t) { return md5_cmn(b ^ c ^ d, a, b, x, s, t); } function md5_ii(a, b, c, d, x, s, t) { return md5_cmn(c ^ (b | (~d)), a, b, x, s, t); } function safe_add(x, y) { let lsw = (x & 0xFFFF) + (y & 0xFFFF); let msw = (x >> 16) + (y >> 16) + (lsw >> 16); return (msw << 16) | (lsw & 0xFFFF); } function bit_rol(num, cnt) { return (num << cnt) | (num >>> (32 - cnt)); } return function (s) { return rstr2hex(rstr_md5(str2rstr_utf8(s))); } })();
// clang-format on

/** POST数据加密处理函数 取自网络孤独行客的脚本 */
function encodeSignData(postData) {
  let SIGN_KEY = "tiebaclient!!!";
  let s = "";
  for (let i in postData) {
    s += i + "=" + postData[i]
  }
  let sign = hex_md5(decodeURIComponent(s) + SIGN_KEY);
  let data = "";
  for (let i in postData) {
    data += "&" + i + "=" + postData[i]
  }
  data += "&sign=" + sign;
  return data.replace("&", "")
}

function formatDate(d) {
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`;
}

function getQueryValue(link, key) {
  let ret = null;
  link.substring(link.indexOf("?") + 1).split("&").forEach(e => {
    let v = e.split("=");
    if (v[0] == key) {
      ret = v[1];
      return false;
    }
  });
  return ret;
}

function xhr(request) {
  return new Promise((success, error) => {
    GM_xmlhttpRequest(Object.assign(request, {
      onload(response) { success(response) },
      onerror(response) { error(response) }
    }));
  });
}

function sleep(time) {
  return new Promise(success => window.setTimeout(success, time));
}

function clamp(val, min, max) {
  return val < min ? min : val > max ? max : val;
}

/** 当前日期 */
const CUR_DATE = Math.floor(new Date().getTime() / 86400000 + 0.333333333);
/** 签到间隔 */
let interval = GM_getValue("interval", 650);
/** 签到黑名单 */
let blacklist = GM_getValue("blacklist", []);
/** 签到浮窗横坐标（百分比） */
let widgetLeft = GM_getValue("widgetLeft", 50);
/** 签到浮窗纵坐标（百分比） */
let widgetTop = GM_getValue("widgetTop", 100);
/** 是否自动签到 */
let autoSign = GM_getValue("autoSign", true);

// 获取用户名
let username;
if (location.host == "www.baidu.com") {
  username = unsafeWindow.bds.comm.user;
} else if (location.host == "tieba.baidu.com") {
  username = unsafeWindow.PageData.user.name || unsafeWindow.PageData.user.user_name;
}

// 创建悬浮窗
let signWidget;
let messageArea;
function setWidgetPos(x, y) {
  widgetLeft = x;
  widgetTop = y;
  signWidget.style.left = `${x}%`;
  signWidget.style.top = `${y}%`;
  signWidget.style.transform = `translate(-${x}%, -${y}%)`;
  GM_setValue("widgetLeft", x);
  GM_setValue("widgetTop", y);
}
if (username != "") {
  signWidget = document.createElement("div");
  document.body.insertBefore(signWidget, document.body.firstChild);
  signWidget.id = "sign-widget";
  signWidget.setAttribute("show", "control");
  setWidgetPos(widgetLeft, widgetTop);

  let signDrag = document.createElement("div");
  signWidget.appendChild(signDrag);
  signDrag.id = "sign-drag";
  signDrag.addEventListener("mousedown", e => {
    function onMousemove(e) {
      let x = clamp((e.clientX - offsetX) / (document.documentElement.clientWidth - signWidget.clientWidth), 0, 1) * 100;
      let y = clamp((e.clientY - offsetY) / (document.documentElement.clientHeight - signWidget.clientHeight), 0, 1) * 100;
      setWidgetPos(x, y);
    }
    function onMouseup() {
      document.body.removeAttribute("dragging");
      window.removeEventListener("mousemove", onMousemove);
      window.removeEventListener("mouseup", onMouseup);
    }
    let offsetX = e.offsetX;
    let offsetY = e.offsetY;
    document.body.setAttribute("dragging", "");
    window.addEventListener("mousemove", onMousemove);
    window.addEventListener("mouseup", onMouseup);
  });

  let ctrlBox = document.createElement("span");
  signWidget.appendChild(ctrlBox);
  ctrlBox.id = "sign-control";

  let btnSign = document.createElement("button");
  ctrlBox.appendChild(btnSign);
  btnSign.setAttribute("sign-btn", "");
  btnSign.id = "sign-btn";
  btnSign.innerHTML = SIGN_ICON;
  btnSign.onclick = signAll;

  let btnSettings = document.createElement("label");
  ctrlBox.appendChild(btnSettings);
  btnSettings.setAttribute("sign-btn", "");
  btnSettings.id = "sign-settings";
  btnSettings.innerHTML = SETTINGS_ICON;
  btnSettings.onclick = openSettings;

  messageArea = document.createElement("div");
  messageArea.id = "sign-message";
  signWidget.appendChild(messageArea);
}

function openSettings() {
  // 创建设置模态框
  let modal = document.createElement("div");
  modal.id = "sign-modal";
  document.body.insertBefore(modal, document.body.firstChild);

  let oldShow = signWidget.getAttribute("show");
  signWidget.setAttribute("show", "none");
  let btnClose = document.createElement("button");
  modal.appendChild(btnClose);
  btnClose.setAttribute("sign-btn", "");
  btnClose.id = "sign-modal-close";
  btnClose.innerHTML = CLOSE_ICON;
  btnClose.onclick = () => {
    modal.remove();
    signWidget.setAttribute("show", oldShow);
  };

  let wrap = document.createElement("div");
  modal.appendChild(wrap);
  wrap.id = "sign-settings-wrap";

  wrap.innerHTML = `\
<p>
  屏蔽列表
  <input id="sign-blacklist-edit"> <a href="javascript:;" id="sign-blacklist-add">添加</a>
  <ul id="sign-blacklist"></ul>
</p>
<p>
  签到间隔
  <input id="sign-interval-edit"> ms<br>
  <small>间隔太小会导致签到失败</small>
</p>
<p>
  自动签到
  <input type="checkbox" id="sign-auto">
</p>
<p>
  浮窗位置<br>
  <input type="radio" id="sign-pos-1" name="sign-pos">
  <input type="radio" id="sign-pos-2" name="sign-pos">
  <input type="radio" id="sign-pos-3" name="sign-pos"><br>
  <input type="radio" id="sign-pos-4" name="sign-pos">
  <input type="radio" id="sign-pos-5" name="sign-pos">
  <input type="radio" id="sign-pos-6" name="sign-pos"><br>
  <input type="radio" id="sign-pos-7" name="sign-pos">
  <input type="radio" id="sign-pos-8" name="sign-pos">
  <input type="radio" id="sign-pos-9" name="sign-pos">
</p>`;

  let ul = document.getElementById("sign-blacklist");
  function append(text) {
    let li = document.createElement("li");
    ul.appendChild(li);
    li.textContent = text;
    let deleteBtn = document.createElement("a");
    li.appendChild(deleteBtn);
    deleteBtn.href = "javascript:;";
    deleteBtn.textContent = "删除";
    deleteBtn.onclick = () => {
      blacklist.splice(blacklist.indexOf(text), 1);
      li.remove();
      GM_setValue("blacklist", blacklist);
    };
  }
  for (let i of blacklist) {
    append(i);
  }

  let blacklistEntry = document.getElementById("sign-blacklist-edit");
  document.getElementById("sign-blacklist-add").onclick = () => {
    blacklist.push(blacklistEntry.value);
    append(blacklistEntry.value);
    GM_setValue("blacklist", blacklist);
  };

  let intervalEntry = document.getElementById("sign-interval-edit");
  intervalEntry.value = interval;
  intervalEntry.onchange = () => {
    interval = parseInt(intervalEntry.value) || 650;
    GM_setValue("interval", interval);
  };

  let autoCheck = document.getElementById("sign-auto");
  autoCheck.checked = autoSign;
  autoCheck.onclick = () => {
    autoSign = autoCheck.checked;
    GM_setValue("autoSign", autoCheck.checked);
  };

  for (let i = 1; i <= 9; i++) {
    let radio = document.getElementById("sign-pos-" + i);
    let x = (i - 1) % 3 * 50;
    let y = Math.floor((i - 1) / 3) * 50;
    radio.onclick = () => setWidgetPos(x, y);
    if (widgetLeft === x && widgetTop === y) {
      radio.checked = true;
    }
  }
}

// 自动签到
let signResults = GM_getValue("signResults", {});
if (username != "") {
  if (!signResults[username]) {
    signResults[username] = {
      _date: [0, 0]
    };
  }
  let [beginDate, endDate] = signResults[username]._date;
  if (beginDate != CUR_DATE && autoSign) {
    signAll();
  } else if (beginDate != endDate) {
    signWidget.setAttribute("show", "all");
    messageArea.textContent = "上次签到未完成或同时打开了多个标签";
  }
}

// 获取贴吧列表
async function getTiebaList() {
  let tiebaList = [];
  for (let pageId = 1; ; pageId++) {
    messageArea.textContent = `获取贴吧列表第 ${pageId} 页`;
    let response = await xhr({
      method: "GET",
      url: "http://tieba.baidu.com/f/like/mylike?pn=" + pageId,
      headers: { "cookie": encodeURIComponent(document.cookie) }
    });
    let doc = new DOMParser().parseFromString(response.responseText, "text/html");
    let rows = Array.from(doc.getElementsByTagName("tr")).slice(1);
    for (let i of rows) {
      tiebaList.push({
        name: i.children[0].textContent,
        exp: parseInt(i.getElementsByClassName("cur_exp")[0].textContent),
        lvName: i.getElementsByClassName("like_badge_title")[0].textContent,
        lv: parseInt(i.getElementsByClassName("like_badge_lv")[0].textContent)
      });
    }
    if (doc.getElementById("j_pagebar").textContent.indexOf("下一页") == -1) {
      return tiebaList;
    }
  }
}

async function sign(tieba) {
  let tiebaPage = await xhr({
    method: "GET",
    url: "http://tieba.baidu.com/mo/m?kw=" + encodeURIComponent(tieba),
    headers: {
      "cookie": encodeURIComponent(document.cookie),
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "User-Agent": "Mozilla/5.0 (SymbianOS/9.3; Series60/3.2 NokiaE72-1/021.021; Profile/MIDP-2.1 Configuration/CLDC-1.1 ) AppleWebKit/525 (KHTML, like Gecko) Version/3.0 BrowserNG/7.1.16352"
    },
  });
  let doc = new DOMParser().parseFromString(tiebaPage.responseText, "text/html");
  let rightPart = doc.querySelector("[style=\"text-align:right;\"]");
  if (rightPart == null) {
    return {success: false, noretry: true, message: "不支持"};
  } else if (rightPart.children[0].tagName == "SPAN") {
    return {success: false, noretry: true, message: "已签到"};
  }
  let postData = {
    "_client_id": "03-00-DA-59-05-00-72-96-06-00-01-00-04-00-4C-43-01-00-34-F4-02-00-BC-25-09-00-4E-36",
    "_client_type": "4",
    "_client_version": "1.2.1.17",
    "_phone_imei": "540b43b59d21b7a4824e1fd31b08e9a6",
    "fid": getQueryValue(rightPart.children[0].href, "fid"),
    "kw": encodeURIComponent(tieba),
    "net_type": "3",
    "tbs": getQueryValue(rightPart.children[0].href, "tbs")
  };
  let result = await xhr({
    method: "POST",
    url: "http://c.tieba.baidu.com/c/c/forum/sign",
    data: decodeURI(encodeSignData(postData)),
    headers: {
      "Content-Type": "application/x-www-form-urlencoded"
    }
  });
  let msg = JSON.parse(result.responseText);
  if (msg.error_code != 0) {
    return {success: false, message: msg.error_msg};
  }
  return {
    success: true,
    gain: parseInt(msg.user_info.sign_bonus_point),
    rank: parseInt(msg.user_info.user_sign_rank),
    continued: parseInt(msg.user_info.cont_sign_num),
    total: parseInt(msg.user_info.total_sign_num),
    missed: parseInt(msg.user_info.miss_sign_num)
  };
}

async function signTry(statusArea, tiebaName) {
  let noretry = false;
  try {
    statusArea.textContent = "签到中";
    let result = await sign(tiebaName);
    if (result.success || result.noretry) {
      result.date = CUR_DATE;
      signResults[username][tiebaName] = result;
      GM_setValue("signResults", signResults);
    }
    if (result.success) {
      statusArea.outerHTML = `<td>${result.gain}</td><td>${result.rank}</td><td>${result.continued}</td><td>${result.total}</td><td>${result.missed}</td>`;
      signResults[username][tiebaName] = result;
      return true;
    } else {
      statusArea.textContent = result.message;
      noretry = result.noretry;
    }
  } catch (e) {
    statusArea.textContent = "错误: " + e.toString();
    console.error("贴吧自动签到错误！", e);
  }
  if (!noretry) {
    let retryBtn = document.createElement("a");
    statusArea.appendChild(retryBtn);
    retryBtn.href = "javascript:;";
    retryBtn.textContent = "重试";
    retryBtn.insertAdjacentText("beforebegin", " ");
    retryBtn.onclick = async () => {
      await signTry(statusArea, tiebaName);
    };
  }
  return false;
}

async function signAll() {
  signWidget.setAttribute("show", "message");

  let aborted = false;
  let finished = false;
  let tiebaList;
  try {
    tiebaList = await getTiebaList();
  } catch (e) {
    console.error("贴吧自动签到错误！", e);
    signWidget.setAttribute("show", "all");
    messageArea.textContent = "错误: " + e.message;
    return;
  }

  // 创建详情按钮
  let btnDetails = document.createElement("a");
  messageArea.appendChild(btnDetails);
  btnDetails.href = "javascript:;";
  btnDetails.textContent = "详细";
  btnDetails.insertAdjacentText("beforebegin", " ");
  btnDetails.onclick = () => {
    signModal.removeAttribute("hide");
    signWidget.setAttribute("show", "none");
  };

  // 创建取消按钮
  let btnAbort = document.createElement("a");
  messageArea.appendChild(btnAbort);
  btnAbort.href = "javascript:;";
  btnAbort.textContent = "放弃";
  btnAbort.insertAdjacentText("beforebegin", " ");
  btnAbort.onclick = () => {
    signModal.remove();
    signWidget.setAttribute("show", finished ? "control" : "all");
    messageArea.textContent = "上次签到未完成";
    aborted = true;
  };

  // 创建签到模态框
  let signModal = document.createElement("div");
  signModal.id = "sign-modal";
  signModal.setAttribute("hide", "");
  document.body.insertBefore(signModal, document.body.firstChild);

  let btnClose = document.createElement("button");
  signModal.appendChild(btnClose);
  btnClose.setAttribute("sign-btn", "");
  btnClose.id = "sign-modal-close";
  btnClose.innerHTML = CLOSE_ICON;
  btnClose.onclick = () => btnAbort.click();

  let btnMinimize = document.createElement("button");
  signModal.appendChild(btnMinimize);
  btnMinimize.setAttribute("sign-btn", "");
  btnMinimize.id = "sign-modal-minimize";
  btnMinimize.innerHTML = MINIMIZE_ICON;
  btnMinimize.onclick = () => {
    signModal.setAttribute("hide", "");
    signWidget.setAttribute("show", finished ? "all" : "message");
  };

  let modalHeader = document.createElement("div");
  modalHeader.id = "sign-modal-header";
  signModal.appendChild(modalHeader);
  modalHeader.textContent = `${username}, ${formatDate(new Date())}, ${tiebaList.length}个吧, 版本${VERSION}`;

  let statusAreaList = [];
  let wrap = document.createElement("div");
  signModal.appendChild(wrap);
  wrap.id = "sign-modal-wrap";
  let table = document.createElement("table");
  wrap.appendChild(table);
  let tr = document.createElement("tr");
  tr.innerHTML = `<th>名称</th><th>等级</th><th>经验</th><th>获得</th><th>排名</th><th>连续</th><th>总计</th><th>漏签</th>`;
  table.append(tr);
  tiebaList.forEach(e => {
    tr = document.createElement("tr");
    table.appendChild(tr);
    tr.innerHTML = `<td><a href="http://tieba.baidu.com/${encodeURIComponent(e.name)}" target="_blank">${e.name}</a></td><td>${e.lv} ${e.lvName}</td><td>${e.exp}</td>`;
    let td = document.createElement("td");
    tr.appendChild(td);
    td.colSpan = 5;
    statusAreaList.push(td);
  });

  let successCount = 0;
  let failedCount = 0;
  // 记录签到日期
  signResults[username]._date[0] = CUR_DATE;
  GM_setValue("signResults", signResults);
  for (let i = 0; i < tiebaList.length; i++) {
    let tiebaName = tiebaList[i].name;
    let statusArea = statusAreaList[i];
    let result = signResults[username][tiebaName] || {};
    wrap.scrollTo({
      top: statusArea.offsetTop + (statusArea.clientHeight - wrap.clientHeight) / 2,
      behavior: "smooth"
    });
    if (aborted) {
      return;
    }
    if (blacklist.indexOf(tiebaName) != -1) {
      failedCount++;
      statusArea.textContent = "已屏蔽";
      continue;
    } else if (result.date == CUR_DATE) {
      if (result.success) {
        successCount++;
        statusArea.outerHTML = `<td>${result.gain}</td><td>${result.rank}</td><td>${result.continued}</td><td>${result.total}</td><td>${result.missed}</td>`;
      } else {
        failedCount++;
        statusArea.textContent = result.message;
      }
      continue;
    }
    messageArea.firstChild.data = `正在签到: ${i + 1}/${tiebaList.length}`;
    if (await signTry(statusArea, tiebaName)) {
      successCount++;
    } else {
      failedCount++;
    }
    await sleep(interval);
  }
  signResults[username]._date[1] = CUR_DATE;
  GM_setValue("signResults", signResults);
  messageArea.firstChild.data = `签到成功${successCount}个，失败${failedCount}个`;
  btnAbort.textContent = "完成";
  signWidget.setAttribute("show", "all");
  finished = true;
}
