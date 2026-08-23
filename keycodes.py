"""QMK keycode tables and name/number conversion.

Only the parts VIA actually round-trips are here: the basic HID keycodes,
the quantum layer/mod ranges, and VIA's custom-keycode block. Add entries
to BASIC freely -- nothing else needs to change.
"""

# Basic keycodes: number -> (name, label shown on the key cap)
BASIC = {
    0x0000: ("KC_NO", ""),
    0x0001: ("KC_TRNS", "▽"),

    0x0004: ("KC_A", "A"), 0x0005: ("KC_B", "B"), 0x0006: ("KC_C", "C"),
    0x0007: ("KC_D", "D"), 0x0008: ("KC_E", "E"), 0x0009: ("KC_F", "F"),
    0x000A: ("KC_G", "G"), 0x000B: ("KC_H", "H"), 0x000C: ("KC_I", "I"),
    0x000D: ("KC_J", "J"), 0x000E: ("KC_K", "K"), 0x000F: ("KC_L", "L"),
    0x0010: ("KC_M", "M"), 0x0011: ("KC_N", "N"), 0x0012: ("KC_O", "O"),
    0x0013: ("KC_P", "P"), 0x0014: ("KC_Q", "Q"), 0x0015: ("KC_R", "R"),
    0x0016: ("KC_S", "S"), 0x0017: ("KC_T", "T"), 0x0018: ("KC_U", "U"),
    0x0019: ("KC_V", "V"), 0x001A: ("KC_W", "W"), 0x001B: ("KC_X", "X"),
    0x001C: ("KC_Y", "Y"), 0x001D: ("KC_Z", "Z"),

    0x001E: ("KC_1", "1"), 0x001F: ("KC_2", "2"), 0x0020: ("KC_3", "3"),
    0x0021: ("KC_4", "4"), 0x0022: ("KC_5", "5"), 0x0023: ("KC_6", "6"),
    0x0024: ("KC_7", "7"), 0x0025: ("KC_8", "8"), 0x0026: ("KC_9", "9"),
    0x0027: ("KC_0", "0"),

    0x0028: ("KC_ENT", "Enter"), 0x0029: ("KC_ESC", "Esc"),
    0x002A: ("KC_BSPC", "Bksp"), 0x002B: ("KC_TAB", "Tab"),
    0x002C: ("KC_SPC", "Space"), 0x002D: ("KC_MINS", "-"),
    0x002E: ("KC_EQL", "="), 0x002F: ("KC_LBRC", "["),
    0x0030: ("KC_RBRC", "]"), 0x0031: ("KC_BSLS", "\\"),
    0x0032: ("KC_NUHS", "#"), 0x0033: ("KC_SCLN", ";"),
    0x0034: ("KC_QUOT", "'"), 0x0035: ("KC_GRV", "`"),
    0x0036: ("KC_COMM", ","), 0x0037: ("KC_DOT", "."),
    0x0038: ("KC_SLSH", "/"), 0x0039: ("KC_CAPS", "Caps"),

    0x003A: ("KC_F1", "F1"), 0x003B: ("KC_F2", "F2"),
    0x003C: ("KC_F3", "F3"), 0x003D: ("KC_F4", "F4"),
    0x003E: ("KC_F5", "F5"), 0x003F: ("KC_F6", "F6"),
    0x0040: ("KC_F7", "F7"), 0x0041: ("KC_F8", "F8"),
    0x0042: ("KC_F9", "F9"), 0x0043: ("KC_F10", "F10"),
    0x0044: ("KC_F11", "F11"), 0x0045: ("KC_F12", "F12"),

    0x0046: ("KC_PSCR", "PrtSc"), 0x0047: ("KC_SCRL", "ScrLk"),
    0x0048: ("KC_PAUS", "Pause"), 0x0049: ("KC_INS", "Ins"),
    0x004A: ("KC_HOME", "Home"), 0x004B: ("KC_PGUP", "PgUp"),
    0x004C: ("KC_DEL", "Del"), 0x004D: ("KC_END", "End"),
    0x004E: ("KC_PGDN", "PgDn"), 0x004F: ("KC_RGHT", "→"),
    0x0050: ("KC_LEFT", "←"), 0x0051: ("KC_DOWN", "↓"),
    0x0052: ("KC_UP", "↑"),

    0x0053: ("KC_NUM", "NumLk"), 0x0054: ("KC_PSLS", "P/"),
    0x0055: ("KC_PAST", "P*"), 0x0056: ("KC_PMNS", "P-"),
    0x0057: ("KC_PPLS", "P+"), 0x0058: ("KC_PENT", "PEnt"),
    0x0059: ("KC_P1", "P1"), 0x005A: ("KC_P2", "P2"),
    0x005B: ("KC_P3", "P3"), 0x005C: ("KC_P4", "P4"),
    0x005D: ("KC_P5", "P5"), 0x005E: ("KC_P6", "P6"),
    0x005F: ("KC_P7", "P7"), 0x0060: ("KC_P8", "P8"),
    0x0061: ("KC_P9", "P9"), 0x0062: ("KC_P0", "P0"),
    0x0063: ("KC_PDOT", "P."), 0x0064: ("KC_NUBS", "\\"),
    0x0065: ("KC_APP", "Menu"),

    0x0068: ("KC_F13", "F13"), 0x0069: ("KC_F14", "F14"),
    0x006A: ("KC_F15", "F15"), 0x006B: ("KC_F16", "F16"),
    0x006C: ("KC_F17", "F17"), 0x006D: ("KC_F18", "F18"),
    0x006E: ("KC_F19", "F19"), 0x006F: ("KC_F20", "F20"),
    0x0070: ("KC_F21", "F21"), 0x0071: ("KC_F22", "F22"),
    0x0072: ("KC_F23", "F23"), 0x0073: ("KC_F24", "F24"),

    0x00A5: ("KC_PWR", "Power"), 0x00A6: ("KC_SLEP", "Sleep"),
    0x00A7: ("KC_WAKE", "Wake"), 0x00A8: ("KC_MUTE", "Mute"),
    0x00A9: ("KC_VOLU", "Vol+"), 0x00AA: ("KC_VOLD", "Vol-"),
    0x00AB: ("KC_MNXT", "Next"), 0x00AC: ("KC_MPRV", "Prev"),
    0x00AD: ("KC_MSTP", "Stop"), 0x00AE: ("KC_MPLY", "Play"),
    0x00AF: ("KC_MSEL", "Media"), 0x00B0: ("KC_EJCT", "Eject"),
    0x00B1: ("KC_MAIL", "Mail"), 0x00B2: ("KC_CALC", "Calc"),
    0x00B3: ("KC_MYCM", "Files"), 0x00B4: ("KC_WSCH", "Search"),
    0x00B5: ("KC_WHOM", "Home"), 0x00B6: ("KC_WBAK", "Back"),
    0x00B7: ("KC_WFWD", "Fwd"), 0x00B8: ("KC_WSTP", "Stop"),
    0x00B9: ("KC_WREF", "Reload"), 0x00BA: ("KC_WFAV", "Fav"),
    0x00BB: ("KC_MFFD", "FFwd"), 0x00BC: ("KC_MRWD", "Rewind"),
    0x00BD: ("KC_BRIU", "Bright+"), 0x00BE: ("KC_BRID", "Bright-"),

    0x00E0: ("KC_LCTL", "Ctrl"), 0x00E1: ("KC_LSFT", "Shift"),
    0x00E2: ("KC_LALT", "Alt"), 0x00E3: ("KC_LGUI", "Win"),
    0x00E4: ("KC_RCTL", "RCtrl"), 0x00E5: ("KC_RSFT", "RShift"),
    0x00E6: ("KC_RALT", "RAlt"), 0x00E7: ("KC_RGUI", "RWin"),
}

# Quantum keycode ranges (QMK 0.19+ / VIA protocol 12)
QK_MOD_TAP = 0x2000
QK_LAYER_TAP = 0x4000
QK_TO = 0x5200
QK_MOMENTARY = 0x5220
QK_DEF_LAYER = 0x5240
QK_TOGGLE_LAYER = 0x5260
QK_ONE_SHOT_LAYER = 0x5280

# Macro n is QK_MACRO + n. VIA writes the macro bodies separately, into the
# macro buffer; this is just the keycode that fires slot n.
QK_MACRO = 0x7700

# VIA's custom-keycode block: index i in the definition's customKeycodes
# array is QK_KB_0 + i.
QK_KB_0 = 0x7E00

# Modifier-combined keycodes: QMK packs "Ctrl+C" into one 16-bit keycode as
# (mods << 8) | basic_keycode. Bit 4 of the mod nibble means "right-hand
# modifiers", and it applies to the whole group - you cannot mix left Ctrl
# with right Shift in a single keycode.
QK_MODS_MIN = 0x0100
QK_MODS_MAX = 0x1FFF
MOD_RIGHT = 0x10

MODS = [("LCTL", 0x01), ("LSFT", 0x02), ("LALT", 0x04), ("LGUI", 0x08)]
MOD_SHORT = {"LCTL": "Ctl", "LSFT": "Sft", "LALT": "Alt", "LGUI": "Win"}

# Handy combinations offered in the picker. Add freely.
SHORTCUTS = [
    "LCTL(KC_C)", "LCTL(KC_V)", "LCTL(KC_X)", "LCTL(KC_Z)", "LCTL(KC_Y)",
    "LCTL(KC_A)", "LCTL(KC_S)", "LCTL(KC_F)", "LCTL(KC_W)", "LCTL(KC_T)",
    "LCTL(KC_TAB)", "LALT(KC_TAB)", "LALT(KC_F4)",
    "LGUI(KC_L)", "LGUI(KC_D)", "LGUI(KC_E)", "LGUI(KC_TAB)",
    "LGUI(KC_LEFT)", "LGUI(KC_RGHT)", "LGUI(KC_UP)", "LGUI(KC_DOWN)",
    "LCTL(LSFT(KC_ESC))", "LCTL(LSFT(KC_T))", "LCTL(LSFT(KC_V))",
    "LGUI(LSFT(KC_S))", "LCTL(LALT(KC_DEL))",
]

SHORTCUT_NAMES = {
    "LCTL(KC_C)": "copy", "LCTL(KC_V)": "paste", "LCTL(KC_X)": "cut",
    "LCTL(KC_Z)": "undo", "LCTL(KC_Y)": "redo", "LCTL(KC_A)": "select all",
    "LCTL(KC_S)": "save", "LCTL(KC_F)": "find", "LCTL(KC_W)": "close tab",
    "LCTL(KC_T)": "new tab", "LCTL(KC_TAB)": "next tab",
    "LALT(KC_TAB)": "switch window", "LALT(KC_F4)": "close window",
    "LGUI(KC_L)": "lock the PC", "LGUI(KC_D)": "show desktop",
    "LGUI(KC_E)": "open Explorer", "LGUI(KC_TAB)": "task view",
    "LGUI(KC_LEFT)": "snap window left",
    "LGUI(KC_RGHT)": "snap window right",
    "LGUI(KC_UP)": "maximise window", "LGUI(KC_DOWN)": "minimise window",
    "LCTL(LSFT(KC_ESC))": "Task Manager",
    "LCTL(LSFT(KC_T))": "reopen closed tab",
    "LCTL(LSFT(KC_V))": "paste without formatting",
    "LGUI(LSFT(KC_S))": "screenshot snip",
    "LCTL(LALT(KC_DEL))": "security screen",
}


_SHORTCUT_CANONICAL = None


def _shortcut_description(name):
    """Look up a shortcut description regardless of how the mods were nested.

    LGUI(LSFT(KC_S)) and LSFT(LGUI(KC_S)) are the same keycode, so the table
    is re-keyed by whatever spelling the decoder produces.
    """
    global _SHORTCUT_CANONICAL
    if _SHORTCUT_CANONICAL is None:
        _SHORTCUT_CANONICAL = {}
        for spelling, description in SHORTCUT_NAMES.items():
            code = _encode_mods(spelling)
            decoded = _decode_mods(code) if code is not None else None
            _SHORTCUT_CANONICAL[decoded[0] if decoded else spelling] = (
                description)
    return _SHORTCUT_CANONICAL.get(name)


def _decode_mods(keycode):
    """Decode a modifier-combined keycode, or None if it is not one."""
    mods = (keycode >> 8) & 0x1F
    base = keycode & 0xFF
    if not mods or base not in BASIC:
        return None

    right = bool(mods & MOD_RIGHT)
    names, shorts = [], []
    for mod_name, bit in MODS:
        if mods & bit:
            names.append("R" + mod_name[1:] if right else mod_name)
            shorts.append(("R" if right else "") + MOD_SHORT[mod_name])
    if not names:
        return None

    name = BASIC[base][0]
    for mod_name in reversed(names):
        name = f"{mod_name}({name})"
    tail = BASIC[base][1] or BASIC[base][0].replace("KC_", "")
    return name, "+".join(shorts + [tail])


def _encode_mods(text):
    """Parse LCTL(KC_C) / LCTL(LSFT(KC_ESC)) into one keycode, or None."""
    mods = 0
    while True:
        for mod_name, bit in MODS:
            for prefix, right in ((mod_name, 0),
                                  ("R" + mod_name[1:], MOD_RIGHT)):
                if text.startswith(prefix + "(") and text.endswith(")"):
                    mods |= bit | right
                    text = text[len(prefix) + 1:-1].strip()
                    break
            else:
                continue
            break
        else:
            break

    if not mods:
        return None
    base = NAME_TO_CODE.get(text)
    if base is None or base > 0xFF:
        return None
    return ((mods & 0x1F) << 8) | base


# Named quantum keycodes this board actually uses. Values are QMK's, verified
# against positions in the factory keymap.c.
QUANTUM = {
    0x700B: ("GU_TOGG", "WinLock"),
    0x7820: ("RGB_TOG", "RGB"),
    0x7821: ("RGB_MOD", "RGB+"),
    0x7822: ("RGB_RMOD", "RGB-"),
    0x7823: ("RGB_HUI", "Hue+"),
    0x7824: ("RGB_HUD", "Hue-"),
    0x7825: ("RGB_SAI", "Sat+"),
    0x7826: ("RGB_SAD", "Sat-"),
    0x7827: ("RGB_VAI", "Bright+"),
    0x7828: ("RGB_VAD", "Bright-"),
    0x7829: ("RGB_SPI", "Speed+"),
    0x782A: ("RGB_SPD", "Speed-"),
    0x7C00: ("QK_BOOT", "Bootloader"),
    0x7C01: ("QK_RBT", "Reboot"),
    0x7C03: ("EE_CLR", "EE_CLR"),
    0x7C33: ("NK_TOGG", "NKRO"),
}

# Vendor keycodes past the end of Epomaker's customKeycodes list. The
# definition JSON only names indices 0-7; these were identified by matching
# matrix positions against the factory keymap.c.
VENDOR_BY_INDEX = {
    19: ("KC_BT1", "BT1"),
    20: ("KC_BT2", "BT2"),
    21: ("KC_BT3", "BT3"),
    24: ("KC_2G4", "2.4G"),
}

# Plain-English descriptions, shown in the picker and the status bar.
FRIENDLY = {
    "KC_BT1": "Bluetooth slot 1", "KC_BT2": "Bluetooth slot 2",
    "KC_BT3": "Bluetooth slot 3", "KC_2G4": "2.4GHz dongle",
    "EE_CLR": "ERASES ALL REMAPS", "QK_BOOT": "ENTERS DFU MODE",
    "QK_RBT": "reboots the keyboard",
    "GU_TOGG": "lock/unlock the Windows key",
    "NK_TOGG": "toggle N-key rollover",
    "RGB_TOG": "lighting on/off", "RGB_MOD": "next lighting effect",
    "RGB_RMOD": "previous lighting effect",
    "RGB_HUI": "hue up", "RGB_HUD": "hue down",
    "RGB_SAI": "saturation up", "RGB_SAD": "saturation down",
    "RGB_VAI": "brightness up", "RGB_VAD": "brightness down",
    "RGB_SPI": "effect speed up", "RGB_SPD": "effect speed down",
    "KC_NO": "nothing - dead key", "KC_TRNS": "fall through to layer below",
    "KC_ESC": "Escape", "KC_BSPC": "Backspace", "KC_ENT": "Enter",
    "KC_SPC": "Space", "KC_TAB": "Tab", "KC_CAPS": "Caps Lock",
    "KC_LSFT": "left Shift", "KC_RSFT": "right Shift",
    "KC_LCTL": "left Ctrl", "KC_RCTL": "right Ctrl",
    "KC_LALT": "left Alt", "KC_RALT": "right Alt",
    "KC_LGUI": "left Windows key", "KC_RGUI": "right Windows key",
    "KC_DEL": "Delete", "KC_INS": "Insert", "KC_PSCR": "Print Screen",
    "KC_MUTE": "mute volume", "KC_VOLU": "volume up",
    "KC_VOLD": "volume down", "KC_MPLY": "play/pause",
    "KC_MNXT": "next track", "KC_MPRV": "previous track",
    "KC_GRV": "backtick / tilde", "KC_MINS": "minus", "KC_EQL": "equals",
    "KC_LBRC": "left bracket", "KC_RBRC": "right bracket",
    "KC_BSLS": "backslash", "KC_SCLN": "semicolon",
    "KC_QUOT": "apostrophe", "KC_COMM": "comma", "KC_DOT": "full stop",
    "KC_SLSH": "forward slash", "KC_APP": "menu key",
}

# Remapping these costs you something you may not be able to get back.
PROTECTED = {
    "KC_BT1": "This is how you switch to Bluetooth slot 1.",
    "KC_BT2": "This is how you switch to Bluetooth slot 2.",
    "KC_BT3": "This is how you switch to Bluetooth slot 3.",
    "KC_2G4": "This is how you switch to the 2.4GHz dongle.",
    "EE_CLR": "This key erases all remaps back to factory.",
    "QK_BOOT": "This key puts the keyboard into DFU mode.",
}


def describe(name):
    """Plain-English description of a keycode name, or '' if we have none."""
    if name in FRIENDLY:
        return FRIENDLY[name]
    shortcut = _shortcut_description(name)
    if shortcut:
        return shortcut
    if name.startswith("MACRO("):
        return f"runs macro slot {name[6:-1]}"
    if name.startswith("MO("):
        return f"hold for layer {name[3:-1]}"
    if name.startswith("TO("):
        return f"switch to layer {name[3:-1]}"
    if name.startswith("TG("):
        return f"toggle layer {name[3:-1]}"
    if name.startswith("DF("):
        return f"make layer {name[3:-1]} the default"
    if name.startswith("OSL("):
        return f"one-shot layer {name[4:-1]}"
    if name.startswith("LT("):
        inner = name[3:-1].split(",")
        if len(inner) == 2:
            return f"tap for {inner[1]}, hold for layer {inner[0]}"
    return ""


LAYER_PREFIXES = [
    ("MO", QK_MOMENTARY), ("TO", QK_TO), ("TG", QK_TOGGLE_LAYER),
    ("DF", QK_DEF_LAYER), ("OSL", QK_ONE_SHOT_LAYER),
]

NAME_TO_CODE = {name: code for code, (name, _) in BASIC.items()}


def decode(keycode, custom=None):
    """Turn a raw keycode into (name, short label for the keycap)."""
    custom = custom or []

    if keycode in BASIC:
        return BASIC[keycode]

    if keycode in QUANTUM:
        return QUANTUM[keycode]

    if QK_MODS_MIN <= keycode <= QK_MODS_MAX:
        combined = _decode_mods(keycode)
        if combined:
            return combined

    if QK_MACRO <= keycode < QK_MACRO + 128:
        return f"MACRO({keycode - QK_MACRO})", f"M{keycode - QK_MACRO}"

    if QK_KB_0 <= keycode < QK_KB_0 + 256:
        index = keycode - QK_KB_0
        if index < len(custom):
            entry = custom[index]
            return entry.get("name", f"CUSTOM({index})"), entry.get(
                "shortName", entry.get("name", f"CK{index}")
            )
        if index in VENDOR_BY_INDEX:
            return VENDOR_BY_INDEX[index]
        return f"CUSTOM({index})", f"CK{index}"

    for prefix, base in LAYER_PREFIXES:
        if base <= keycode < base + 32:
            layer = keycode - base
            return f"{prefix}({layer})", f"{prefix}{layer}"

    if QK_LAYER_TAP <= keycode < QK_LAYER_TAP + 0x1000:
        layer = (keycode >> 8) & 0x0F
        tap = keycode & 0xFF
        tap_name = BASIC.get(tap, (f"0x{tap:02X}", ""))[0]
        return f"LT({layer},{tap_name})", f"LT{layer}"

    if QK_MOD_TAP <= keycode < QK_MOD_TAP + 0x2000:
        tap = keycode & 0xFF
        tap_name = BASIC.get(tap, (f"0x{tap:02X}", ""))[0]
        return f"MT({tap_name})", "MT"

    return f"0x{keycode:04X}", f"{keycode:04X}"


def encode(text, custom=None, layers=4):
    """Parse a keycode name back to a number. Returns None if unparseable."""
    custom = custom or []
    text = text.strip().upper()

    if text in NAME_TO_CODE:
        return NAME_TO_CODE[text]

    combined = _encode_mods(text)
    if combined is not None:
        return combined

    for code, (name, _label) in QUANTUM.items():
        if name == text:
            return code

    for index, (name, _label) in VENDOR_BY_INDEX.items():
        if name == text:
            return QK_KB_0 + index

    for index, entry in enumerate(custom):
        if entry.get("name", "").upper() == text:
            return QK_KB_0 + index

    if text.startswith("MACRO(") and text.endswith(")"):
        try:
            index = int(text[6:-1])
        except ValueError:
            return None
        return QK_MACRO + index if 0 <= index < 128 else None

    for prefix, base in LAYER_PREFIXES:
        if text.startswith(prefix + "(") and text.endswith(")"):
            try:
                layer = int(text[len(prefix) + 1:-1])
            except ValueError:
                return None
            if 0 <= layer < layers:
                return base + layer
            return None

    if text.startswith("LT(") and text.endswith(")"):
        try:
            layer_text, tap_text = text[3:-1].split(",", 1)
            layer = int(layer_text)
        except ValueError:
            return None
        tap = NAME_TO_CODE.get(tap_text.strip())
        if tap is None or not 0 <= layer < 16:
            return None
        return QK_LAYER_TAP | (layer << 8) | (tap & 0xFF)

    if text.startswith("0X"):
        try:
            return int(text, 16)
        except ValueError:
            return None

    return None


def catalog(custom=None, layers=4, macros=0):
    """Every keycode the picker offers, as (name, label) pairs."""
    custom = custom or []
    items = [
        (name, label) for code, (name, label) in sorted(BASIC.items())
        if name != "KC_NO"
    ]
    items += [
        (entry.get("name", f"CK{i}"), entry.get("shortName", ""))
        for i, entry in enumerate(custom)
    ]
    for prefix, _ in LAYER_PREFIXES:
        items += [(f"{prefix}({n})", "") for n in range(layers)]
    items += [(f"MACRO({n})", f"M{n}") for n in range(macros)]
    items += [(name, label) for _code, (name, label) in sorted(
        QUANTUM.items()) if name not in ("QK_BOOT",)]
    items += [(name, label) for _i, (name, label) in sorted(
        VENDOR_BY_INDEX.items())]
    for combo in SHORTCUTS:
        code = encode(combo)
        items.append((combo, decode(code)[1] if code else combo))
    return items
