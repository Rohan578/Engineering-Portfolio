# Resume Badge (ESP32-C5 + 2" ST7789)

A pocket Wi-Fi hotspot that shows pixel-art night scenes of the portfolio's
hero on its screen. When someone joins the network, their phone opens a page
styled like the portfolio homepage (labeled **RESUME**) with a button to view
the PDF, and the screen flips through resume pages.

```
device/
  resume_badge/resume_badge.ino   the firmware (open this folder in Arduino IDE)
  sd/                             copy everything in here onto the SD card
  previews/                       PNGs of each screen
```

## Setup

1. **SD card:** format it FAT32 and copy the *contents* of `device/sd/` to the
   root of the card (so the card has `Rohan_Shrivastava_Resume.pdf`,
   `scenes/`, and `web/` at the top level).
2. **Arduino IDE:** install "Adafruit ST7789 and ST7735 Library" and
   "Adafruit GFX Library". Board: **ESP32C5 Dev Module**, USB CDC On Boot:
   **Enabled**. The default partition scheme works (the sketch uses about
   1.17 MB of the 1.25 MB app space, out of 4 MB of flash).
3. Open `resume_badge/resume_badge.ino` and upload.

Wiring is listed at the top of the sketch.

## Controls

| BOOT button | Idle | Someone connected |
| --- | --- | --- |
| Tap | next screensaver | next resume page |
| Hold 5 s | Wi-Fi off | Wi-Fi off |

Screensavers: **The Shore** (side view on the cliff over the ocean),
**The Plains** (from behind, in a grassy plain), **The Vigil** (facing you,
hands on his sword), and **Relic** (floating sword).

## Changing the art

All screens are made from the same sprites as the website, so the hero always
matches. Edit `tools/generate_art.py` (the hero) or `tools/device_art.py` (the
badge scenes and cover), then run:

```
pip install pillow fonttools brotli
python3 tools/generate_art.py
python3 tools/device_art.py
```

and copy `device/sd/` to the card again. No firmware change is needed.

**Updating the resume:** replace `Rohan_Shrivastava_Resume.pdf` on the card.
