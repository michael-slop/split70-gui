# Split70 Configurator

A small, hackable VIA client for the Epomaker Split70 (and any other
VIA-enabled QMK keyboard). Remaps keys and drives RGB over raw HID.

Written because the Epomaker Hub and both VIA builds refused to detect the
board, even though the firmware answers VIA commands perfectly.

## Why this exists

The Split70 exposes a vendor-defined HID interface:

```
HID\VID_342D&PID_E491&MI_01   ->   usage page 0xFF60, usage 0x61
```

That is the standard QMK raw-HID endpoint. Asking it for its VIA protocol
version returns **12**, so the firmware is fully VIA-capable. The problem was
never the keyboard - it was the configurator apps failing to match a
definition to it.

This app skips all of that and talks to the interface directly.

## Requirements

- Windows
- Python 3.9+ with tkinter (`python -c "import tkinter"` should be silent)
- No pip packages. Everything goes through ctypes and the Win32 HID DLLs.

## Running

```
python app.py
```

Or double-click `run.cmd`.

Pass a different definition if you want:

```
python app.py path\to\some_other_keyboard.json
```

The keyboard must be connected **by USB cable**. Bluetooth and 2.4GHz modes
do not expose the raw-HID interface.

Only one client at a time. The app opens the VIA interface exclusively,
because two clients sharing it interleave their requests and each can read
the other's reply - which returns wrong data silently instead of failing.
A second instance gets a clear "already in use" error instead.

## Using it

- **Layer buttons** switch between the keyboard's 4 layers.
- **Click any key** to remap it. Search by name (`KC_ESC`), or type a layer
  key like `MO(1)`, a layer-tap like `LT(1,KC_SPC)`, or a raw `0x00A8`.
- Writes go straight to the keyboard's EEPROM. There is no separate save
  step for the keymap - it persists across unplugging.
- **Lighting** changes apply live; hit *Save lighting to keyboard* to make
  them survive a power cycle.
- Hovering a key shows its matrix position, raw keycode, and a
  plain-English description in the status bar.
- **About / Help** in the toolbar has the wireless keys, the layer map, the
  macro syntax, and the keys worth not touching.
- The picker searches descriptions as well as names, so typing `blue` finds
  the Bluetooth keys and `layer 1` finds `MO(1)`, `TO(1)`, `TG(1)`, `DF(1)`.
- Remapping `KC_BT1`/`KC_BT2`/`KC_BT3`/`KC_2G4`/`EE_CLR` asks for
  confirmation first - those are expensive to lose.

## Shortcuts on a single key

A modifier plus a key packs into one keycode, so a shortcut does not need a
macro slot. Type any of these into the picker's search box:

| You type | Keycap shows | Does |
| --- | --- | --- |
| `LCTL(KC_C)` | `Ctl+C` | copy |
| `LGUI(KC_L)` | `Win+L` | lock the PC |
| `LALT(KC_F4)` | `Alt+F4` | close window |
| `LCTL(LSFT(KC_ESC))` | `Ctl+Sft+Esc` | Task Manager |
| `LGUI(LSFT(KC_S))` | `Sft+Win+S` | screenshot snip |

Nest them freely - `LCTL(LSFT(KC_T))` is Ctrl+Shift+T. Common ones are in
the picker already and searchable by description (`copy`, `lock`, `snap`).
`LCTL`/`LSFT`/`LALT`/`LGUI` are left-hand; `RCTL` and friends are
right-hand. You cannot mix left and right in one keycode - QMK has a single
"use right-hand modifiers" bit that applies to the whole group.

Add your own to `SHORTCUTS` and `SHORTCUT_NAMES` in `keycodes.py`.

**Shortcut or macro?** A shortcut is one chord, fires instantly, costs no
macro slot. Use a macro when you need a *sequence*, a delay, or literal
text.

## Macros

Hit **Macros...** in the toolbar. The Split70 has **16 slots sharing 3322
bytes**. Pick a slot on the left, write the body on the right, then
*Write all to keyboard*.

There are two editing styles, and the radio buttons at the top convert
between them without losing what you have typed. A live pane underneath the
editor spells out what the macro will actually do, and shows the error
inline if it does not compile.

### Plain English (the default)

One step per line:

| You write | It does |
| --- | --- |
| `press win+shift+s` | holds Win and Shift, taps S, releases both |
| `press alt+4` | Alt+4 |
| `ctrl+c` | a bare chord means `press` |
| `tap enter` | taps one key, no modifiers |
| `hold shift` / `release shift` | for holds that span several steps |
| `type some text` | sends the text literally |
| `wait 250` | pauses 250 ms (`250ms` works too) |
| `# note` | comment |

Modifier names are forgiving: `ctrl`/`control`, `alt`/`opt`/`option`,
`win`/`super`/`cmd`/`gui`, `shift`. Keys take their obvious spelling -
`enter`, `esc`, `pgdn`, `f13`, `.` or `period`. Prefix `r` for the
right-hand modifier (`ralt`, `rwin`).

A line that is not a recognised statement is treated as `type`, so a plain
line of text needs no keyword.

This all lives in `macrolang.py`, which only compiles to the raw syntax
below - the keyboard never sees anything else.

### Raw

The wire syntax that goes into the macro buffer:

| You write | It does |
| --- | --- |
| `hello` | types `hello` |
| `{KC_ENT}` | taps Enter |
| `{+KC_LSFT}` | holds Shift down |
| `{-KC_LSFT}` | releases Shift |
| `{250}` | waits 250 ms |
| `{{` | a literal `{` |

So `{+KC_LSFT}hi{-KC_LSFT}{500}!` types `HI`, waits half a second, then `!`.
The same thing in plain English is `hold shift`, `type hi`, `release shift`,
`wait 500`, `type !`.

To fire a macro, remap a key to `MACRO(0)`, `MACRO(1)`, and so on - they
show up in the normal keycode picker.

Macro steps take **basic keycodes only** (`KC_A`, `KC_ENT`, `KC_LSFT`...).
That's a firmware limit, not this app's: the macro buffer stores one byte
per keycode, so 16-bit quantum keycodes like `MO(1)` cannot appear in a
macro body. The editor rejects them rather than writing something the
keyboard would misread.

The bytes-used counter is live - if you overrun 3322 bytes, the write is
refused before anything is sent.

## Files

| File | What's in it |
| --- | --- |
| `via_hid.py` | Device discovery + the VIA protocol. No GUI code. |
| `keycodes.py` | Keycode tables and name/number conversion. |
| `macros.py` | Macro body encoding/decoding. No GUI code. |
| `macrolang.py` | The plain-English macro language. No GUI code. |
| `app.py` | The tkinter GUI: layout rendering, picker, lighting, macros. |
| `Epomaker_Split70.json` | VIA definition - layout, RGB menus, custom keycodes. |

## Hacking on it

**Add a keycode** you need: drop an entry in `BASIC` in `keycodes.py`.
Nothing else has to change; the picker and the decoder both read that table.
`QUANTUM` holds the non-basic ones (RGB controls, `EE_CLR`, `GU_TOGG`), and
`FRIENDLY` holds the plain-English descriptions.

**Vendor keycodes.** Epomaker's definition JSON names only custom keycode
indices 0-7, but the firmware uses more than that. The wireless keys were
identified by matching matrix positions against the factory `keymap.c`:

| Keycode | Index | Is |
| --- | --- | --- |
| `0x7E13` | 19 | `KC_BT1` |
| `0x7E14` | 20 | `KC_BT2` |
| `0x7E15` | 21 | `KC_BT3` |
| `0x7E18` | 24 | `KC_2G4` |

They live in `VENDOR_BY_INDEX` in `keycodes.py`. Without it they show as
`CUSTOM(19)` and friends. If you find what `MOR_1`..`MOR_4` do, add them
there too - the published source does not say.

**Use it with another keyboard**: pass that keyboard's VIA definition JSON on
the command line. `via_hid.find_devices()` matches on the 0xFF60/0x61 usage
pair rather than on a specific VID/PID, so any VIA board is fair game. The
lighting panel assumes VIA custom channel 3, which is the QMK RGB matrix
convention - change `LIGHTING_CHANNEL` in `app.py` if yours differs.

**Script it instead of clicking**, no GUI involved:

```python
import via_hid, keycodes

vid, pid, path = via_hid.find_devices()[0]
with via_hid.ViaDevice(path) as kb:
    print(kb.protocol_version(), kb.layer_count())
    kb.set_keycode(0, 0, 0, keycodes.NAME_TO_CODE["KC_ESC"])
```

**Bulk edits** are easy this way too - `read_keymap()` gives you
`keymap[layer][row][col]`, and `set_keycode()` writes one back.

**Macros from a script**, no GUI either:

```python
import via_hid, macros

vid, pid, path = via_hid.find_devices()[0]
with via_hid.ViaDevice(path) as kb:
    count, size = kb.macro_count(), kb.macro_buffer_size()
    bodies = macros.split_buffer(kb.read_macro_buffer(size), count)
    bodies[0] = macros.encode_macro("git status{KC_ENT}")
    kb.write_macro_buffer(macros.join_buffer(bodies, size))
```

Read the buffer, swap the slots you care about, write it back - the whole
buffer moves as one blob, so always start from a read.

## A warning

`via_hid.py` defines `CMD_BOOTLOADER_JUMP = 0x0B`. Sending it drops the
keyboard into DFU mode and it stops working as a keyboard until reflashed.
Nothing in this app sends it. Leave it that way unless you mean it.

`CMD_EEPROM_RESET = 0x0A` wipes all your remaps back to firmware defaults.
Also unused here.

`macro_reset()` (VIA `0x10`) clears every macro slot. The GUI never calls
it - *Clear this slot* only edits the in-memory copy until you write.

## Wireless keys

These are on the **function layer**, not the base layer, so they are not
visible on layer 0 in the GUI:

| Keys | Does |
| --- | --- |
| `Fn` + `Q` / `W` / `E` | switch to Bluetooth slot 1 / 2 / 3 (`KC_BT1`..`KC_BT3`) |
| `Fn` + `R` | switch to the 2.4GHz dongle (`KC_2G4`) |
| hold either 3-5 seconds | re-pair that slot |

The keyboard forces USB mode whenever a cable is connected (`HS_BAT_CABLE_PIN`
in the firmware), so unplug it before expecting either radio to work. A
2.4GHz connection also needs the dongle actually plugged into the computer.

If wireless "stops working", check those three things before suspecting the
keymap: cable unplugged, switch position, dongle present.

### Resuming wireless after unplugging the cable

Unplugging does not bring the radio back on its own. **Flick the power
switch off and on.** A power cycle re-runs init, which restores your
last-used mode from EEPROM:

```c
wireless_devs_change(!confinfo.devs, confinfo.devs, false);
```

That beats pressing Fn+Q, because it returns you to whichever mode you were
last on rather than forcing a specific slot. Verified: cable out, switch
off and on, Bluetooth connected in about 6 seconds.

The switch is power, not mode - nothing selects the radio by switch on this
firmware, since `HS_BT_DEF_PIN` and `HS_2G4_DEF_PIN` are commented out and
the mode-scan call sits behind `#if defined(...)` on both.

The 30-second "revert to USB" timeout in `hs_rgb_blink_hook` is a red
herring. It is only reachable via `lpwr_wakeup_hook`, which fires once per
wake, so it never repeats often enough to elapse.

## The corner LEDs (an undocumented second zone)

The Split70 has a few LEDs at the top of each half that are not under any
keycap. They ignore every control in the Lighting box and sit there cycling
a rainbow forever. This is not a bug in this app - it took probing the
hardware to find out why.

**What the firmware says.** `keyboard.json` declares 77 RGB matrix LEDs for
72 keys, split `[36, 41]` between the halves. Five of them have no real
home: six entries claim matrix `[0, 0]` at coordinate `(0, 0)`, three at the
head of each half's chain, and only one of those can be the actual key at
row 0 column 0. Every gradient, cycle and spiral effect derives colour from
an LED's x/y, so LEDs pinned to the origin just rotate hue forever no matter
which effect you pick.

**What actually drives them.** VIA's custom-value protocol has numbered
channels, and channel 2 is `id_qmk_rgblight` - a second lighting zone,
separate from the `id_qmk_rgb_matrix` zone on channel 3. The Split70's
firmware implements channel 2, but Epomaker's definition JSON never declares
it, so neither VIA nor the Epomaker Hub offers any control for it. Probing
the device directly found it answering:

    ch2 id2 (effect) = 14      <- an rgblight rainbow-swirl mode
    ch2 id3 (speed)  = 0
    ch2 id4 (colour) = hue 0, sat 255

Setting `ch2 id2` to 0 turns them off. The **Corner LEDs** box in the app
drives that channel - effect, brightness, speed and colour - and its own
Save button commits it to EEPROM so it survives unplugging.

The box greys itself out on a keyboard without that zone: an unsupported
custom value reads back as `0xFF`, and every real rgblight mode is far below
that, which tells the two apart.

## Layers: the Windows/Mac trap

The Split70 has four layers, and they are **two pairs**, not four
independent ones:

| Layer | What it is |
| --- | --- |
| 0 | Windows base |
| 1 | Windows Fn |
| 2 | macOS base |
| 3 | macOS Fn |

Layers 0 and 2 differ by exactly 11 keys - `KC_LGUI`/`KC_LALT` swapped at
`4,2` and `4,3`, `KC_RALT`/`KC_RGUI` at `9,3`, some punctuation, and the Fn
key itself, which is `MO(1)` on layer 0 and `MO(3)` on layer 2.

Two keys move you between the pairs:

* **Fn + S** is `TO(2)` on layer 1 - jumps to macOS.
* **Fn + A** is `TO(0)` on layer 3 - jumps back to Windows.

Note the asymmetry: from Windows, only `Fn+S` does anything; from macOS,
only `Fn+A` does. A stray `Fn+S` therefore looks exactly like the keyboard
forgetting everything you configured. It has not - your remaps are still in
EEPROM on layers 0 and 1, but the board has stopped reading them, and the Fn
key now opens layer 3, which is nearly empty.

**If your remaps and macros suddenly do nothing and the Fn layer seems dead,
press Fn+A before you suspect anything else.** Nothing is lost.

The practical consequence: if you actually use both modes, remap **both
pairs**. Anything you put on layer 0 or 1 is invisible in macOS mode.

## Matrix notes

The Split70 is a 10x9 matrix. Rows 0-4 are the left half (row 0, col 0 is
the knob press - it ships as `KC_MUTE`), rows 5-9 are the right half. Slots
reading `KC_NO` are matrix positions with no physical key.

## Sources and references

All Python here is original. Nothing was forked or vendored. These are the
sources the behaviour was derived from.

**[Epomaker/split70](https://github.com/Epomaker/split70)** - the official
QMK keyboard source, GPL-2.0-or-later. Read as reference, not copied. It is
where the following came from:

- the factory keymap, used to identify vendor keycodes by matrix position
  (`KC_BT1`..`KC_BT3`, `KC_2G4` at `QK_KB_0` indices 19-21 and 24, which
  Epomaker's VIA definition does not name)
- the RGB indicator indices (`HS_RGB_INDEX_CAPS`, `HS_RGB_BLINK_INDEX_BT1`
  and friends) and their colours
- the wireless behaviour: `confinfo.devs` restore on init, the cable
  forcing USB mode, and `hs_rgb_blink_hook` being unreachable in practice
- the RGB record feature (`RGBREC_CHANNEL_NUM`, the `RGBR_PLAY` effect)

Note that the repository is **incomplete**: `post_rules.mk` includes a
`wireless/` directory that is not published, and `wls/wls.h` does
`#include "wireless.h"` from it. The source therefore cannot be compiled as
released, which is why building custom firmware for this board is not
practical.

**[Epomaker Split70 VIA definition](https://epomaker.com/blogs/via-json/epomaker-split70-json)**
- `Epomaker_Split70.json`, bundled here unmodified. Epomaker's file, not
ours. Supplies the physical layout, the RGB menu ids, and custom keycode
names 0-7.

**[QMK Firmware](https://github.com/qmk/qmk_firmware)** - the keycode value
ranges (`QK_MODS`, `QK_MOD_TAP`, `QK_LAYER_TAP`, `QK_TO`, `QK_MOMENTARY`,
`QK_MACRO`, `QK_KB_0`, the RGB and magic blocks) and the macro buffer
encoding used in `macros.py`.

**[VIA](https://github.com/the-via/app)** - the raw-HID protocol this
speaks: command ids `0x01`-`0x13`, the `0xFF60`/`0x61` usage pair, and the
custom-value channel model used for lighting.

**Also consulted:**
[SRGBmods/EpomakerQMK](https://github.com/SRGBmods/EpomakerQMK) for the
Split70 VIA mapping, and [vial-qmk](https://github.com/vial-kb/vial-qmk)
when checking whether Vial was viable on this board. It is not - the
firmware answers `0xFE` (Vial's keyboard-id command) with `0xFF`,
"unhandled", so Vial cannot see it without reflashing.

### Licence

MIT - see [LICENSE](LICENSE). That covers the Python and the documentation,
which are original work.

It does not cover `Epomaker_Split70.json`, which is Epomaker's file,
redistributed unmodified for convenience.

No code from Epomaker's GPL firmware is included here. It was read as
reference to identify keycode values and hardware indices, which are facts
about the hardware rather than copied source.
