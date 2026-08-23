"""A plain-English front end for macro bodies.

`macros.py` speaks the wire syntax - {+KC_LSFT}{KC_S}{-KC_LSFT} and so on.
That is precise, but it is a poor thing to type by hand: you have to know the
QMK spelling of every key, and a chord means naming each modifier twice.

This module sits on top of it. You write:

    press win+shift+s
    wait 200
    type hello world

and `compile_script` turns that into the wire syntax, which `macros.encode`
then turns into bytes. `decompile` goes back the other way, so the editor can
show either view of the same macro.

Statements, one per line, `#` starts a comment:

    press <chord>     hold the modifiers, tap the key, release the modifiers
    tap <key>         tap one key, no modifiers
    hold <key>        press and do not release
    release <key>     release a held key
    type <text>       send the text literally
    wait <ms>         pause

A bare chord is shorthand for `press`, so `ctrl+c` on its own line works.
Anything that is not a recognised statement is treated as `type`, which makes
the common case - a line of text - need no keyword at all.
"""

import re

import keycodes

# Modifier words. Everything on the left resolves to the keycode on the
# right; the aliases exist because people reach for different names on
# different platforms and all of them should just work.
MODIFIERS = {
    "ctrl": "KC_LCTL", "control": "KC_LCTL", "lctrl": "KC_LCTL",
    "rctrl": "KC_RCTL",
    "shift": "KC_LSFT", "sft": "KC_LSFT", "lshift": "KC_LSFT",
    "rshift": "KC_RSFT",
    "alt": "KC_LALT", "opt": "KC_LALT", "option": "KC_LALT",
    "lalt": "KC_LALT", "ralt": "KC_RALT", "altgr": "KC_RALT",
    "win": "KC_LGUI", "super": "KC_LGUI", "cmd": "KC_LGUI",
    "command": "KC_LGUI", "gui": "KC_LGUI", "meta": "KC_LGUI",
    "lwin": "KC_LGUI", "rwin": "KC_RGUI",
}

# Friendly names for keys whose QMK spelling is not guessable.
KEY_ALIASES = {
    "enter": "KC_ENT", "return": "KC_ENT", "ret": "KC_ENT",
    "esc": "KC_ESC", "escape": "KC_ESC",
    "space": "KC_SPC", "spacebar": "KC_SPC",
    "tab": "KC_TAB",
    "backspace": "KC_BSPC", "bksp": "KC_BSPC", "bs": "KC_BSPC",
    "delete": "KC_DEL", "del": "KC_DEL",
    "insert": "KC_INS", "ins": "KC_INS",
    "home": "KC_HOME", "end": "KC_END",
    "pageup": "KC_PGUP", "pgup": "KC_PGUP",
    "pagedown": "KC_PGDN", "pgdn": "KC_PGDN",
    "up": "KC_UP", "down": "KC_DOWN", "left": "KC_LEFT", "right": "KC_RGHT",
    "capslock": "KC_CAPS", "caps": "KC_CAPS",
    "printscreen": "KC_PSCR", "prtsc": "KC_PSCR", "prntscrn": "KC_PSCR",
    "scrolllock": "KC_SCRL", "pause": "KC_PAUS",
    "menu": "KC_APP", "app": "KC_APP",
    "comma": "KC_COMM", "period": "KC_DOT", "dot": "KC_DOT",
    "slash": "KC_SLSH", "backslash": "KC_BSLS",
    "semicolon": "KC_SCLN", "quote": "KC_QUOT", "apostrophe": "KC_QUOT",
    "grave": "KC_GRV", "backtick": "KC_GRV", "tilde": "KC_GRV",
    "minus": "KC_MINS", "dash": "KC_MINS", "hyphen": "KC_MINS",
    "equals": "KC_EQL", "equal": "KC_EQL", "plus": "KC_EQL",
    "lbracket": "KC_LBRC", "rbracket": "KC_RBRC",
}

# Single printable characters that name a key directly, so `press ctrl+.`
# and `press ctrl+period` are the same thing.
PUNCTUATION = {
    ",": "KC_COMM", ".": "KC_DOT", "/": "KC_SLSH", ";": "KC_SCLN",
    "'": "KC_QUOT", "[": "KC_LBRC", "]": "KC_RBRC", "-": "KC_MINS",
    "=": "KC_EQL", "`": "KC_GRV",
}

STATEMENTS = ("press", "tap", "hold", "release", "type", "wait", "delay")


class ScriptError(ValueError):
    """Raised when a script line cannot be compiled. Carries the line number."""

    def __init__(self, line_no, message):
        super().__init__(f"line {line_no}: {message}")
        self.line_no = line_no


def resolve_key(word):
    """Turn one friendly key word into a QMK keycode name, or None."""
    word = word.strip()
    if not word:
        return None
    lowered = word.lower()

    if lowered in MODIFIERS:
        return MODIFIERS[lowered]
    if lowered in KEY_ALIASES:
        return KEY_ALIASES[lowered]
    if word in PUNCTUATION:
        return PUNCTUATION[word]

    # f1 - f24
    match = re.fullmatch(r"f([1-9]|1[0-9]|2[0-4])", lowered)
    if match:
        return f"KC_F{match.group(1)}"

    # a single letter or digit
    if len(word) == 1 and word.isalnum():
        return f"KC_{word.upper()}"

    # already a QMK name
    candidate = lowered.upper()
    if not candidate.startswith("KC_"):
        candidate = "KC_" + candidate
    if candidate in keycodes.NAME_TO_CODE:
        return candidate
    return None


def _split_chord(text):
    """Split 'ctrl+shift+esc' into ([mods], key). Raises on a bad chord."""
    # A trailing '+' means the key itself is '+', as in `press ctrl++`.
    if text.endswith("++"):
        parts = text[:-2].split("+") + ["+"]
    else:
        parts = text.split("+")

    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        raise ValueError("empty chord")

    mods, key = [], None
    for index, part in enumerate(parts):
        last = index == len(parts) - 1
        as_mod = MODIFIERS.get(part.lower())
        if as_mod and not last:
            mods.append(as_mod)
            continue
        if last:
            key = resolve_key(part)
            if key is None:
                raise ValueError(f"unknown key '{part}'")
        else:
            raise ValueError(f"'{part}' is not a modifier")
    return mods, key


def _emit_literal(text):
    """Escape text so encode_macro sends it literally."""
    return text.replace("{", "{{")


def compile_line(raw, line_no=1):
    """Compile one script line into wire syntax. Returns '' for blanks."""
    line = raw.strip()
    if not line or line.startswith("#"):
        return ""

    # Split on the first space only, and keep the untrimmed remainder: a
    # trailing space in `type Done: ` is part of what the user wants sent.
    head, _, verbatim = raw.lstrip().partition(" ")
    keyword = head.lower()
    rest = verbatim.strip()

    if keyword in STATEMENTS:
        if keyword == "type":
            return _emit_literal(verbatim)

        if not rest:
            raise ScriptError(line_no, f"'{keyword}' needs something after it")

        if keyword in ("wait", "delay"):
            digits = rest.rstrip("ms").strip() or rest
            if not digits.isdigit():
                raise ScriptError(line_no, f"'{rest}' is not a number of ms")
            return "{" + digits + "}"

        if keyword in ("hold", "release"):
            key = resolve_key(rest)
            if key is None:
                raise ScriptError(line_no, f"unknown key '{rest}'")
            return "{" + ("+" if keyword == "hold" else "-") + key + "}"

        if keyword == "tap":
            key = resolve_key(rest)
            if key is None:
                raise ScriptError(line_no, f"unknown key '{rest}'")
            return "{" + key + "}"

        # press
        try:
            mods, key = _split_chord(rest)
        except ValueError as exc:
            raise ScriptError(line_no, str(exc)) from None
        return _chord_syntax(mods, key)

    # No keyword. A chord if it looks like one, otherwise literal text.
    if "+" in line and " " not in line:
        try:
            mods, key = _split_chord(line)
        except ValueError as exc:
            raise ScriptError(line_no, str(exc)) from None
        return _chord_syntax(mods, key)

    single = resolve_key(line) if " " not in line and len(line) > 1 else None
    if single and line.lower() in KEY_ALIASES:
        return "{" + single + "}"

    return _emit_literal(line)


def _chord_syntax(mods, key):
    out = "".join("{+" + m + "}" for m in mods)
    out += "{" + key + "}"
    out += "".join("{-" + m + "}" for m in reversed(mods))
    return out


def compile_script(text):
    """Compile a whole script into wire syntax."""
    out = []
    for number, raw in enumerate(text.splitlines(), start=1):
        out.append(compile_line(raw, number))
    return "".join(out)


# ------------------------------------------------------------------ reverse

_TOKEN = re.compile(r"\{([+-]?)([^}]*)\}")
_MOD_WORD = {
    "KC_LCTL": "ctrl", "KC_RCTL": "rctrl", "KC_LSFT": "shift",
    "KC_RSFT": "rshift", "KC_LALT": "alt", "KC_RALT": "ralt",
    "KC_LGUI": "win", "KC_RGUI": "rwin",
}
_FRIENDLY_KEY = {v: k for k, v in reversed(list(KEY_ALIASES.items()))}


def _word_for(name):
    """Friendliest spelling of a keycode name."""
    if name in _MOD_WORD:
        return _MOD_WORD[name]
    if name in _FRIENDLY_KEY:
        return _FRIENDLY_KEY[name]
    if re.fullmatch(r"KC_[A-Z0-9]", name):
        return name[3:].lower()
    if re.fullmatch(r"KC_F\d+", name):
        return name[3:].lower()
    return name


def _parse_tokens(wire):
    """Walk wire syntax into (kind, value) pairs."""
    steps, index = [], 0
    while index < len(wire):
        if wire.startswith("{{", index):
            steps.append(("text", "{"))
            index += 2
            continue
        if wire[index] == "{":
            match = _TOKEN.match(wire, index)
            if match:
                sign, body = match.group(1), match.group(2).strip()
                index = match.end()
                if body.isdigit():
                    steps.append(("wait", int(body)))
                else:
                    kind = {"+": "hold", "-": "release", "": "tap"}[sign]
                    steps.append((kind, body))
                continue
        steps.append(("text", wire[index]))
        index += 1
    return steps


def decompile(wire):
    """Best-effort turn of wire syntax back into a readable script."""
    steps = _parse_tokens(wire)
    lines, index, pending = [], 0, []

    def flush():
        if pending:
            lines.append("type " + "".join(pending))
            pending.clear()

    while index < len(steps):
        kind, value = steps[index]

        if kind == "text":
            pending.append(value)
            index += 1
            continue

        # Look for hold(s) ... tap ... release(s) and fold it into a chord.
        if kind == "hold":
            mods, scan = [], index
            while scan < len(steps) and steps[scan][0] == "hold" \
                    and steps[scan][1] in _MOD_WORD:
                mods.append(steps[scan][1])
                scan += 1
            if mods and scan < len(steps) and steps[scan][0] == "tap":
                key = steps[scan][1]
                tail = scan + 1
                released = []
                while tail < len(steps) and steps[tail][0] == "release" \
                        and steps[tail][1] in mods:
                    released.append(steps[tail][1])
                    tail += 1
                if sorted(released) == sorted(mods):
                    flush()
                    words = [_MOD_WORD[m] for m in mods] + [_word_for(key)]
                    lines.append("press " + "+".join(words))
                    index = tail
                    continue

        flush()
        if kind == "wait":
            lines.append(f"wait {value}")
        else:
            lines.append(f"{kind} {_word_for(value)}")
        index += 1

    flush()
    return "\n".join(lines)


def explain(wire):
    """One human sentence per step, for a preview pane."""
    out = []
    for kind, value in _parse_tokens(wire):
        if kind == "text":
            if out and out[-1].startswith("type "):
                out[-1] += value
            else:
                out.append("type " + value)
        elif kind == "wait":
            out.append(f"wait {value} ms")
        elif kind == "hold":
            out.append(f"hold {_word_for(value)} down")
        elif kind == "release":
            out.append(f"release {_word_for(value)}")
        else:
            out.append(f"tap {_word_for(value)}")
    return out
