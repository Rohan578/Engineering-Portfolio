/* =====================================================================
   ESP32-C5 RESUME BADGE - 5 GHz portal + 2" ST7789 TFT (GMT020-02-80)
   Pixel Fantasy edition: same hero and night scenes as the portfolio
   ---------------------------------------------------------------------
   The screens (screensavers + resume pages) are stored in the firmware
   itself (scenes_flash.h, made by tools/device_art.py), so the screen
   works with or without an SD card.

   The SD card is only needed for what the phone downloads:
     /Rohan_Shrivastava_Resume.pdf
     /web/...   art, fonts, and photo for the phone page
   (copy the contents of device/sd/ onto a FAT32 card).
   Without the card the phone page still opens, just without the art,
   and the resume button explains that the PDF isn't available.

   BOOT BUTTON (GPIO28)
     tap         idle: next screensaver | connected: next resume page
     hold 5 s    turn Wi-Fi off and disconnect everyone
   Screensavers: The Shore, The Plains, The Vigil, Relic

   LIBRARIES  "Adafruit ST7789 and ST7735 Library" + "Adafruit GFX Library"
   WIRING     SCK->6 MOSI->1 MISO->8 | SD CS->0 | TFT CS->9 DC->10 RST->23
              VCC->3V3 GND->GND BL->3V3
   ARDUINO    Board "ESP32C5 Dev Module", USB CDC On Boot "Enabled".
              Keep scenes_flash.h in the same folder as this file.
   ===================================================================== */

#include <WiFi.h>
#include <DNSServer.h>
#include <WebServer.h>
#include <SPI.h>
#include <SD.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include "thumbs.h"          // project pictures (tools/device_thumbs.py)
#include "scenes_flash.h"


/* =====================================================================
   1. SETTINGS
   ===================================================================== */
const char* AP_SSID     = "Rohan_Shrivastava";
const char* AP_PASSWORD = "";                 // 8+ characters to require a password
#define AP_BAND_MODE WIFI_BAND_MODE_5G_ONLY
const int AP_CHANNEL = 36;

const int           BOOT_BUTTON_PIN = 28;
const unsigned long HOLD_TIME_MS    = 5000;

const int SD_MISO = 8, SD_SCK = 6, SD_MOSI = 1, SD_CS = 0;
// The SD card shares SPI with the screen. 4 MHz (the library default) is
// reliable on breadboard wiring.
const uint32_t SD_SPI_HZ = 4000000;
#define TFT_CS  9
#define TFT_DC  10
#define TFT_RST 23

const char* RESUME_FILE = "/Rohan_Shrivastava_Resume.pdf";

const bool          AUTO_ADVANCE = false;     // flip resume pages on a timer
const unsigned long PAGE_FLIP_MS = 5000;

// Screensavers: a scene from flash (nullptr = drawn in code) and its caption
struct Saver { const FlashScene* scene; const char* caption; };
const Saver SAVERS[] = {
  { &SCENE_SHORE,  "// the shore"  },
  { &SCENE_PLAINS, "// the plains" },
  { &SCENE_VIGIL,  "// the vigil"  },
  { nullptr,       "// relic"      },
};
const int NUM_SAVERS = sizeof(SAVERS) / sizeof(SAVERS[0]);


/* =====================================================================
   2. PHONE PAGE (same look as the portfolio homepage, but for the resume)
      Art, fonts, and photo come from /web on the SD card. If the card
      isn't readable, the images hide themselves and the page still works.
   ===================================================================== */
const char PAGE_HTML[] PROGMEM = R"HTML(<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rohan Shrivastava | Resume</title>
<style>
@font-face{font-family:P;font-weight:700;src:url(/web/pixelify-700.woff2) format("woff2")}
@font-face{font-family:P;font-weight:500;src:url(/web/pixelify-500.woff2) format("woff2")}
@font-face{font-family:I;src:url(/web/inter-400.woff2) format("woff2")}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;font-family:I,system-ui,sans-serif;color:#e2def5;
 background:url(/web/stars.svg) repeat,linear-gradient(#07061a,#0e0b29);background-size:360px,auto}
.hero{position:relative;height:clamp(470px,62vw,560px);overflow:hidden;
 background:linear-gradient(#05040f,#1a1442 70%,#07061a)}
.hero img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:38% 100%;
 -webkit-mask-image:linear-gradient(#000 55%,transparent);mask-image:linear-gradient(#000 55%,transparent)}
.t{position:absolute;top:4%;left:0;right:0;padding:0 12px;text-align:center}
.t:before{content:"";position:absolute;z-index:-1;left:50%;top:50%;width:min(760px,98vw);height:200%;
 transform:translate(-50%,-50%);background:radial-gradient(ellipse,rgba(5,4,15,.8),rgba(5,4,15,0) 70%)}
.rib{display:inline-block;padding:6px 18px;font:700 16px P,monospace;letter-spacing:.3em;
 color:#f2d98a;background:rgba(10,8,30,.78);border:2px solid rgba(242,217,138,.6)}
h1{margin:10px 0 0;font:700 clamp(32px,9vw,64px)/1.05 P,monospace;color:#fff3c4;
 text-shadow:0 4px 0 #2a1d57,0 0 24px rgba(242,217,138,.25)}
.tag{margin-top:10px;font:500 15px P,monospace;color:#e6e2f8;text-shadow:0 2px 0 #05040f}
.card{display:flex;gap:22px;align-items:center;max-width:680px;margin:-40px auto 32px;position:relative;padding:24px;
 background:rgba(12,10,32,.86);border:2px solid #3b3470}
.pic{flex-shrink:0;text-align:center}
.pic img{display:block;width:120px;height:120px;object-fit:cover;border:2px solid #f2d98a}
.pic span{display:block;margin-top:8px;font:500 13px P,monospace;color:#f2d98a}
.card p{margin:0 0 14px;line-height:1.7}
.btn{display:inline-block;padding:12px 22px;font:700 17px P,monospace;color:#14102e;
 background:#f2d98a;text-decoration:none;border:2px solid #fff3c4}
.note{margin-top:14px;font-size:12px;color:#9896be}
@media(max-width:560px){.card{flex-direction:column;text-align:center;margin:-40px 14px 28px}}
</style></head><body>
<header class="hero"><img src="/web/hero.svg" alt="" onerror="this.remove()">
 <div class="t"><div class="rib">&#10022; RESUME &#10022;</div>
 <h1>Rohan Shrivastava</h1>
 <div class="tag">Hardware &middot; Embedded Systems &middot; Robotics</div></div>
</header>
<section class="card">
 <div class="pic"><img src="/web/profile.jpg" alt="Rohan Shrivastava" onerror="this.remove()"><span>ECE &middot; Rutgers &rsquo;28</span></div>
 <div>
  <p>Hi, I&rsquo;m Rohan &mdash; an Electrical &amp; Computer Engineering student at Rutgers University passionate about hardware design, embedded systems, and robotics. Always building, testing, and scaling new hardware projects.</p>
  <a class="btn" href="/resume.pdf" target="_blank" rel="noopener">&darr; View My Resume</a>
  <div class="note">Full portfolio: rohan578.github.io/Engineering-Portfolio</div>
 </div>
</section>
</body></html>)HTML";

// Shown instead of the PDF when the SD card can't be read
const char NO_RESUME_HTML[] PROGMEM = R"HTML(<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Resume unavailable</title>
<style>body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;
text-align:center;font-family:system-ui,sans-serif;color:#e2def5;background:linear-gradient(#07061a,#1a1442)}
h1{color:#fff3c4;font-size:22px}a{color:#f2d98a}</style></head><body><div>
<h1>The resume download isn&rsquo;t available right now</h1>
<p>This badge couldn&rsquo;t read its SD card. You can find my resume on my portfolio:</p>
<p><a href="https://rohan578.github.io/Engineering-Portfolio/">rohan578.github.io/Engineering-Portfolio</a></p>
<p><a href="/">&larr; Back</a></p></div></body></html>)HTML";


/* =====================================================================
   3. COLORS + STATE
   ===================================================================== */
#define BG      0x10A5
#define PARCH   0xEF3A
#define MUTED   0x8896
#define GOLD    0xF609
#define GOLDDIM 0x8B45
#define WARM    0xFFFF
#define STEEL   0x4AAF

Adafruit_ST7789 tft(&SPI, TFT_CS, TFT_DC, TFT_RST);
DNSServer dnsServer;
WebServer webServer(80);
IPAddress apIP(192, 168, 4, 1);

bool portalActive = true;
bool buttonWasDown = false, longFired = false;
unsigned long buttonPressStart = 0;

enum Mode { SAVER, RESUME };
Mode mode = SAVER;
int  saverType = 0, page = 0;
unsigned long lastFrame = 0, lastFlip = 0;
const unsigned long FRAME_MS = 60;
const int NUM_PAGES = 7;

// SD card: only used for phone downloads, mounted on demand
bool sdReady = false;
unsigned long lastMountTry = 0;
const unsigned long MOUNT_RETRY_MS = 5000;   // don't keep retrying a missing card

// Sky band of the current scene, kept in RAM so a shooting star can be erased
const int SKY_TOP = 16, SKY_ROWS = 144;      // rows 16-159, where shooting stars fly
uint16_t* skyCache = nullptr;                // SKY_ROWS x 240 pixels (69 KB)
bool skyValid = false;

// Twinkling pixels of the current scene (read from flash)
const int MAX_ANIM = 320;
struct AnimPx { uint8_t x, y, w, h; uint16_t on, off, period, offset; bool lit; };
AnimPx anims[MAX_ANIM];
int animCount = 0;

bool shooting = false; int shX = 0, shY = 0, shLife = 0;   // shooting star
float swBob = 0, swAng = 0; int swPrevY = -1;              // relic sword


/* =====================================================================
   4. SD CARD + WEB SERVER
   ===================================================================== */
// Mount (or remount) the card. Rate-limited so a missing card doesn't slow
// every request down.
bool ensureSD(bool forceRemount = false) {
  if (sdReady && !forceRemount) return true;
  if (millis() - lastMountTry < MOUNT_RETRY_MS && lastMountTry != 0) return sdReady;
  lastMountTry = millis();
  SD.end();
  sdReady = SD.begin(SD_CS, SPI, SD_SPI_HZ);
  Serial.println(sdReady ? "SD mounted." : "SD card not readable.");
  return sdReady;
}

File openSD(const char* path) {
  if (!ensureSD()) return File();
  File f = SD.open(path, FILE_READ);
  if (!f && ensureSD(true)) f = SD.open(path, FILE_READ);   // card glitched: remount once
  return f;
}

const char* mimeFor(const String& path) {
  if (path.endsWith(".pdf"))   return "application/pdf";
  if (path.endsWith(".svg"))   return "image/svg+xml";
  if (path.endsWith(".jpg"))   return "image/jpeg";
  if (path.endsWith(".woff2")) return "font/woff2";
  return "application/octet-stream";
}

// Stream a file from SD, with Range support (phones ask for parts of the PDF).
// Returns false if the file couldn't be opened (nothing is sent in that case).
bool sendSDFile(const char* path, bool cacheable) {
  File file = openSD(path);
  if (!file) return false;
  const char* type = mimeFor(path);
  size_t size = file.size();
  if (cacheable) webServer.sendHeader("Cache-Control", "max-age=86400");
  webServer.sendHeader("Accept-Ranges", "bytes");

  if (webServer.hasHeader("Range")) {
    String range = webServer.header("Range");
    long start = 0, end = size - 1;
    int eq = range.indexOf('='), dash = range.indexOf('-');
    if (eq >= 0 && dash > eq) {
      String s = range.substring(eq + 1, dash), e = range.substring(dash + 1);
      if (s.length()) start = s.toInt();
      if (e.length()) end = e.toInt();
    }
    if (end >= (long)size) end = size - 1;
    if (start < 0 || start > end) start = 0;
    size_t len = end - start + 1;
    char cr[48];
    snprintf(cr, sizeof(cr), "bytes %ld-%ld/%u", start, end, (unsigned)size);
    webServer.sendHeader("Content-Range", cr);
    webServer.setContentLength(len);
    webServer.send(206, type, "");
    file.seek(start);
    WiFiClient client = webServer.client();
    static uint8_t buf[1024];
    while (len > 0 && client.connected()) {
      size_t n = file.read(buf, len < sizeof(buf) ? len : sizeof(buf));
      if (n == 0) break;
      client.write(buf, n);
      len -= n;
    }
  } else {
    webServer.streamFile(file, type);
  }
  file.close();
  return true;
}

void handlePage() { webServer.send_P(200, "text/html", PAGE_HTML); }

void handleResume() {
  if (!sendSDFile(RESUME_FILE, false)) webServer.send_P(503, "text/html", NO_RESUME_HTML);
}

void handleOther() {                         // /web/* from SD, anything else -> the page
  String uri = webServer.uri();
  if (uri.startsWith("/web/") && uri.indexOf("..") < 0) {
    if (!sendSDFile(uri.c_str(), true)) webServer.send(404, "text/plain", "Not available.");
  } else {
    handlePage();
  }
}


/* =====================================================================
   5. DRAWING: scenes from flash, twinkles, text
   ===================================================================== */
static uint16_t lineBuf[240 * ART_SCALE];    // one art row = 3 screen rows

// Decode a palette + run-length scene from flash straight to the screen.
void drawFlashScene(const FlashScene& s) {
  const uint8_t* p = s.rle;
  const uint8_t* end = s.rle + s.rleLen;
  uint8_t left = 0, idx = 0;
  for (int ay = 0; ay < ART_H; ay++) {
    for (int ax = 0; ax < ART_W; ax++) {
      if (left == 0 && p + 1 < end) { left = p[0]; idx = p[1]; p += 2; }
      if (left) left--;
      uint16_t c = s.palette[idx];
      lineBuf[ax * 3] = lineBuf[ax * 3 + 1] = lineBuf[ax * 3 + 2] = c;
    }
    memcpy(lineBuf + 240, lineBuf, 480);
    memcpy(lineBuf + 480, lineBuf, 480);
    int y = ay * ART_SCALE, rows = min(ART_SCALE, 320 - y);
    if (rows <= 0) break;
    tft.startWrite();
    tft.setAddrWindow(0, y, 240, rows);
    tft.writePixels(lineBuf, 240 * rows);
    tft.endWrite();
    if (skyCache)
      for (int r = 0; r < rows; r++) {
        int row = y + r - SKY_TOP;
        if (row >= 0 && row < SKY_ROWS) memcpy(skyCache + row * 240, lineBuf, 480);
      }
  }
  skyValid = (skyCache != nullptr);
}

// Copy the scene's animated pixels out of flash.
void loadAnim(const FlashScene& s) {
  animCount = 0;
  if (!s.anim) return;
  for (int i = 0; i < s.animCount && i < MAX_ANIM; i++) {
    const uint8_t* r = s.anim + i * 12;
    AnimPx& a = anims[animCount++];
    a.x = r[0]; a.y = r[1]; a.w = r[2]; a.h = r[3];
    a.on     = r[4]  | (r[5]  << 8);
    a.off    = r[6]  | (r[7]  << 8);
    a.period = r[8]  | (r[9]  << 8);
    a.offset = r[10] | (r[11] << 8);
    a.lit = false;
  }
}

// Twinkle: each pixel shows its "on" color for the first half of its period.
void stepAnims(bool force) {
  unsigned long now = millis();
  for (int i = 0; i < animCount; i++) {
    AnimPx& a = anims[i];
    bool lit = ((now + a.offset) % a.period) < (a.period / 2);
    if (lit != a.lit || force) {
      a.lit = lit;
      tft.fillRect(a.x * ART_SCALE, a.y * ART_SCALE, a.w * ART_SCALE, a.h * ART_SCALE, lit ? a.on : a.off);
    }
  }
}

// Repaint a rectangle of the sky from RAM (erases the shooting star).
void restoreRect(int x, int y, int w, int h) {
  if (!skyValid) return;
  if (x < 0) { w += x; x = 0; }
  if (x + w > 240) w = 240 - x;
  if (y < SKY_TOP) { h -= SKY_TOP - y; y = SKY_TOP; }
  if (y + h > SKY_TOP + SKY_ROWS) h = SKY_TOP + SKY_ROWS - y;
  if (w <= 0 || h <= 0) return;
  tft.startWrite();
  for (int row = y; row < y + h; row++) {
    tft.setAddrWindow(x, row, w, 1);
    tft.writePixels(skyCache + (row - SKY_TOP) * 240 + x, w);
  }
  tft.endWrite();
}

void stepShootingStar() {
  if (!skyValid) { shooting = false; return; }
  if (!shooting && random(0, 1000) < 6) {
    shooting = true; shX = random(10, 120); shY = random(24, 90); shLife = 22;
  }
  if (!shooting) return;
  restoreRect(shX - 1, shY - 1, 9, 6);       // erase the last frame
  shX += 7; shY += 3; shLife--;
  if (shLife <= 0 || shX > 230 || shY > SKY_TOP + SKY_ROWS - 8) { shooting = false; return; }
  tft.drawLine(shX, shY, shX + 6, shY + 3, WARM);
  tft.drawPixel(shX + 6, shY + 3, 0xC69F);
}

// Draw a 1-bit text mask (from scenes_flash.h) in its color.
void drawMask(const TextMask& m) {
  int stride = (m.w + 7) / 8;
  tft.startWrite();
  for (int y = 0; y < m.h; y++) {
    const uint8_t* row = m.bits + y * stride;
    int x = 0;
    while (x < m.w) {
      while (x < m.w && !(row[x >> 3] & (0x80 >> (x & 7)))) x++;
      int start = x;
      while (x < m.w && (row[x >> 3] & (0x80 >> (x & 7)))) x++;
      if (x > start) tft.writeFastHLine(m.x + start, m.y + y, x - start, m.color);
    }
  }
  tft.endWrite();
}

void tp(int x, int y, uint8_t size, uint16_t col, const char* s) {
  tft.setTextSize(size); tft.setTextColor(col); tft.setCursor(x, y); tft.print(s);
}

// Word-wrap without String allocations. Returns the next y.
int wrapPrint(int x, int y, int maxChars, uint8_t size, uint16_t col, const char* text, int lineH) {
  tft.setTextSize(size); tft.setTextColor(col);
  char line[40]; int len = 0;
  const char* p = text;
  while (*p) {
    const char* w = p; while (*p && *p != ' ') p++;
    int wl = p - w;
    if (len && len + 1 + wl > maxChars) { line[len] = 0; tft.setCursor(x, y); tft.print(line); y += lineH; len = 0; }
    if (len) line[len++] = ' ';
    for (int i = 0; i < wl && len < 39; i++) line[len++] = w[i];
    while (*p == ' ') p++;
  }
  if (len) { line[len] = 0; tft.setCursor(x, y); tft.print(line); y += lineH; }
  return y;
}

void drawSprite(const char* const* rows, int nrows, int x, int y, int scale, uint16_t main, uint16_t accent) {
  for (int r = 0; r < nrows; r++)
    for (int c = 0; rows[r][c]; c++) {
      char ch = rows[r][c];
      if (ch == ' ' || ch == '.') continue;
      tft.fillRect(x + c * scale, y + r * scale, scale, scale, ch == 'o' ? accent : main);
    }
}

void sparkle(int x, int y, uint16_t c) {
  tft.drawFastVLine(x, y - 5, 11, c); tft.drawFastHLine(x - 5, y, 11, c);
  tft.drawPixel(x - 2, y - 2, c); tft.drawPixel(x + 2, y - 2, c);
  tft.drawPixel(x - 2, y + 2, c); tft.drawPixel(x + 2, y + 2, c);
}

// Small pixel icons for the resume pages
const char* SPR_SWORD[] = {"  o  ","  o  ","  o  ","  o  ","  o  ","  o  "," ooo ","XoooX","  X  ","  X  ","  X  ","  X  "};
const char* IC_BOOK[]   = {"XXX XXX","XoX XoX","XoX XoX","XoX XoX","XoX XoX","XXX XXX"," XX XX ","       "};


/* =====================================================================
   6. SCREENSAVERS
   ===================================================================== */
void saverChrome(const char* caption) {
  tp(8, 4, 1, GOLDDIM, caption);
  tp(10, 306, 1, MUTED, "Wi-Fi:"); tp(52, 306, 1, GOLD, AP_SSID);
}

void enterSaver() {
  const Saver& s = SAVERS[saverType];
  shooting = false; animCount = 0; skyValid = false;
  if (s.scene) {
    drawFlashScene(*s.scene);
    loadAnim(*s.scene);
    stepAnims(true);
  } else {                                     // Relic: floating sword
    tft.fillScreen(BG);
    for (int i = 0; i < 40; i++) tft.drawPixel(random(0, 240), random(16, 300), i % 4 ? PARCH : WARM);
    swBob = 0; swAng = 0; swPrevY = -1;
  }
  saverChrome(s.caption);
  lastFrame = 0;
}

void stepRelic() {
  int sx = 110, y = 120 + (int)(sin(swBob) * 16);
  if (swPrevY >= 0) tft.fillRect(sx - 2, swPrevY - 2, 24, 52, BG);
  drawSprite(SPR_SWORD, 12, sx, y, 4, STEEL, GOLD);
  swPrevY = y;
  for (int k = 0; k < 3; k++) {
    float a = swAng + k * 2.094;
    tft.drawPixel(120 + (int)(cos(a) * 60), y + 24 + (int)(sin(a) * 30), GOLD);
  }
  swBob += 0.12; swAng += 0.14;
}

void saverStep() {
  if (millis() - lastFrame < FRAME_MS) return;
  lastFrame = millis();
  if (SAVERS[saverType].scene) { stepAnims(false); stepShootingStar(); }
  else stepRelic();
}


/* =====================================================================
   7. RESUME PAGES (shown on the screen while someone is connected)
   ===================================================================== */
void drawFrame() {
  tft.drawRect(2, 2, 236, 316, GOLD); tft.drawRect(5, 5, 230, 310, GOLDDIM);
  const int s = 7;
  tft.fillRect(2, 2, s, s, GOLD);             tft.fillRect(240 - 2 - s, 2, s, s, GOLD);
  tft.fillRect(2, 320 - 2 - s, s, s, GOLD);   tft.fillRect(240 - 2 - s, 320 - 2 - s, s, s, GOLD);
}

void drawDots(int p) {
  const int gap = 14, startX = 120 - ((NUM_PAGES - 1) * gap) / 2;
  for (int i = 0; i < NUM_PAGES; i++) tft.fillCircle(startX + i * gap, 302, 3, i == p ? GOLD : MUTED);
}

// Start page: the portfolio homepage banner, labeled RESUME (all from flash)
void drawCover() {
  drawFlashScene(SCENE_COVER);
  int x0 = COVER_RIBBON[0], y0 = COVER_RIBBON[1], x1 = COVER_RIBBON[2], y1 = COVER_RIBBON[3];
  tft.fillRect(x0, y0, x1 - x0 + 1, y1 - y0 + 1, tft.color565(10, 8, 30));
  tft.drawRect(x0, y0, x1 - x0 + 1, y1 - y0 + 1, tft.color565(160, 144, 104));
  tft.drawRect(x0 + 1, y0 + 1, x1 - x0 - 1, y1 - y0 - 1, tft.color565(160, 144, 104));
  for (int i = 0; i < COVER_TEXT_COUNT; i++) drawMask(COVER_TEXT[i]);
}

// One resume page: label box, project picture in the top-right corner (same
// size on every page), then the title and three bullets underneath.
void questPage(const char* label, const uint16_t* thumb, const char* title, const char* sub,
               const char* b1, const char* b2, const char* b3) {
  tft.fillScreen(BG); drawFrame();
  tft.drawRect(12, 12, 158, 28, GOLDDIM); sparkle(26, 26, GOLD); tp(40, 19, 2, GOLD, label);
  tft.drawRect(177, 11, THUMB + 2, THUMB + 2, GOLDDIM);          // picture border
  tft.drawRGBBitmap(178, 12, thumb, THUMB, THUMB);
  tp(14, 68, 3, PARCH, title);
  int y = 100;
  tp(14, y, 1, MUTED, sub); y += 24;
  y = wrapPrint(14, y, 17, 2, PARCH, b1, 20) + 8;
  y = wrapPrint(14, y, 17, 2, PARCH, b2, 20) + 8;
  wrapPrint(14, y, 17, 2, PARCH, b3, 20);
}

void drawSkills() {
  tft.fillScreen(BG); drawFrame();
  tft.drawRect(12, 12, 216, 28, GOLDDIM); sparkle(26, 26, GOLD); tp(40, 19, 2, GOLD, "SKILLS");
  drawSprite(IC_BOOK, 8, 198, 16, 3, STEEL, GOLD);
  int y = 58;
  tp(14, y, 1, GOLD, "PROGRAMMING");         y += 16;
  y = wrapPrint(14, y, 17, 2, PARCH, "C++ C Python Java MATLAB", 20) + 10;
  tp(14, y, 1, GOLD, "EMBEDDED & HARDWARE"); y += 16;
  y = wrapPrint(14, y, 17, 2, PARCH, "ESP32 RP2040 I2C SPI ESP-NOW", 20) + 10;
  tp(14, y, 1, GOLD, "TOOLS");               y += 16;
  wrapPrint(14, y, 17, 2, PARCH, "KiCad EasyEDA SolidWorks Git", 20);
}

void drawResumePage(int p) {
  skyValid = false; shooting = false;
  switch (p) {
    case 0: drawCover(); break;
    case 1: questPage("GUILD",     THUMB_ACCELIRATE, "Accelirate",  "QA & AI Intern - 2026",
                      "Agentic QA test suites", "Custom SQL edge cases", "Debugged backend"); break;
    case 2: questPage("QUEST IV",  THUMB_SOILNODE,  "Soil Node",   "IoT Plant Monitor - 2026",
                      "Battery IoT soil monitor", "Temp, humidity, moisture", "ESP32-C3 + KiCad PCB"); break;
    case 3: questPage("QUEST III", THUMB_MOTOR,   "Motor V1",    "RU HART - 2026",
                      "Dual motors 20A / 12V", "DRV8701 + RP2040", "Custom KiCad board"); break;
    case 4: questPage("QUEST II",  THUMB_BREATHE, "Breathe.exe", "HackRU '26 Winner",
                      "Horror interview sim", "Glove: ESP32-C3 ESP-NOW", "Unity + Gemini + Presage"); break;
    case 5: questPage("QUEST I",   THUMB_LIDAR,    "Maxbot",      "RU HART LiDAR Bot",
                      "Maps an enclosed space", "Streams outline to web", "ESP32-S3 + LiDAR"); break;
    case 6: drawSkills(); break;
  }
  drawDots(p);
}

void enterResume() { page = 0; drawResumePage(page); lastFlip = millis(); }

void resumeStep() {
  if (!AUTO_ADVANCE || millis() - lastFlip < PAGE_FLIP_MS) return;
  lastFlip = millis(); page = (page + 1) % NUM_PAGES; drawResumePage(page);
}


/* =====================================================================
   8. BOOT BUTTON
   ===================================================================== */
void shutdownPortal() {
  if (!portalActive) return;
  Serial.println("BOOT held 5 s: Wi-Fi off.");
  dnsServer.stop(); webServer.stop();
  WiFi.softAPdisconnect(true); WiFi.mode(WIFI_OFF);
  portalActive = false; skyValid = false;
  tft.fillScreen(BG); drawFrame(); tp(44, 150, 2, MUTED, "Wi-Fi off");
}

void onShortPress() {
  if (!portalActive) return;
  if (mode == SAVER) { saverType = (saverType + 1) % NUM_SAVERS; enterSaver(); }
  else { page = (page + 1) % NUM_PAGES; drawResumePage(page); lastFlip = millis(); }
}

void checkButton() {
  bool down = digitalRead(BOOT_BUTTON_PIN) == LOW;
  if (down && !buttonWasDown) { buttonPressStart = millis(); buttonWasDown = true; longFired = false; }
  else if (down && !longFired && millis() - buttonPressStart >= HOLD_TIME_MS) { longFired = true; shutdownPortal(); }
  else if (!down && buttonWasDown) {
    buttonWasDown = false;
    if (!longFired && millis() - buttonPressStart >= 40) onShortPress();
  }
}


/* =====================================================================
   9. SETUP
   ===================================================================== */
void setup() {
  Serial.begin(115200);
  pinMode(BOOT_BUTTON_PIN, INPUT_PULLUP);
  randomSeed(esp_random());

  SPI.begin(SD_SCK, SD_MISO, SD_MOSI, -1);
  tft.init(240, 320); tft.setRotation(0); tft.invertDisplay(true);
  tft.fillScreen(BG);
  skyCache = (uint16_t*)malloc(SKY_ROWS * 240 * sizeof(uint16_t));
  if (!skyCache) Serial.println("Not enough RAM for the sky cache: shooting stars off.");

  if (ensureSD()) {
    if (!SD.exists(RESUME_FILE))     Serial.println("Missing on SD: resume PDF");
    if (!SD.exists("/web/hero.svg")) Serial.println("Missing on SD: /web (phone page art)");
  } else {
    Serial.println("No SD card: screens work, but phones can't download the resume.");
  }

  WiFi.mode(WIFI_AP);
  WiFi.setBandMode(AP_BAND_MODE);
  WiFi.softAPConfig(apIP, apIP, IPAddress(255, 255, 255, 0));
  WiFi.softAP(AP_SSID, strlen(AP_PASSWORD) >= 8 ? AP_PASSWORD : NULL, AP_CHANNEL);
  Serial.printf("Hotspot %s on channel %d (%s)\n", AP_SSID, WiFi.channel(),
                WiFi.channel() >= 36 ? "5 GHz" : "2.4 GHz - 5 GHz not active");

  const char* headerKeys[] = { "Range" };
  webServer.collectHeaders(headerKeys, 1);
  dnsServer.start(53, "*", apIP);              // every domain -> this badge (captive portal)
  webServer.on("/", handlePage);
  webServer.on("/resume.pdf", handleResume);
  webServer.onNotFound(handleOther);
  webServer.begin();

  mode = SAVER; enterSaver();
  Serial.println("Ready.");
}


/* =====================================================================
   10. LOOP
   ===================================================================== */
void loop() {
  if (portalActive) {
    dnsServer.processNextRequest();
    webServer.handleClient();
    Mode want = WiFi.softAPgetStationNum() > 0 ? RESUME : SAVER;
    if (want != mode) { mode = want; mode == SAVER ? enterSaver() : enterResume(); }
    if (mode == SAVER) saverStep(); else resumeStep();
  }
  checkButton();
}
