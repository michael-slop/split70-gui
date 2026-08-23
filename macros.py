"""Macro body encoding for VIA's dynamic macro buffer.

The buffer holds one null-terminated body per slot, back to back. Inside a
body, printable ASCII is sent literally; anything else is an escape led by
SS_QMK_PREFIX (0x01):

    01 01 kc      tap keycode
    01 02 kc      hold keycode down
    01 03 kc      release keycode
    01 04 lo hi   delay, ms = (lo - 1) + (hi - 1) * 255

Keycodes here are single-byte basic HID codes, not the 16-bit quantum
keycodes used in the keymap.

The text syntax this module reads and writes:

    hello           types "hello"
    {KC_ENT}        taps Enter
    {+KC_LSFT}      holds Shift down
    {-KC_LSFT}      releases Shift
    {250}           waits 250 ms
    {{              a literal { character
"""

import keycodes

SS_QMK_PREFIX = 0x01
SS_TAP = 0x01
SS_DOWN = 0x02
SS_UP = 0x03
SS_DELAY = 0x04

MAX_DELAY = 254 * 255 + 254  # what the two-byte encoding can express


class MacroError(ValueError):
    """Raised when a macro body cannot be parsed."""


def _delay_bytes(ms):
    ms = max(0, min(int(ms), MAX_DELAY))
    return [(ms % 255) + 1, (ms // 255) + 1]


def encode_macro(text):
    """Turn the text syntax into raw macro bytes."""
    out = bytearray()
    i = 0
    while i < len(text):
        char = text[i]

        if char == "{":
            if text.startswith("{{", i):
                out.append(ord("{"))
                i += 2
                continue

            end = text.find("}", i)
            if end == -1:
                raise MacroError("unclosed '{' - every { needs a matching }")
            token = text[i + 1:end].strip()
            i = end + 1

            if not token:
                raise MacroError("empty {} is not a valid step")

            if token.isdigit():
                out += bytes([SS_QMK_PREFIX, SS_DELAY] + _delay_bytes(token))
                continue

            action = SS_TAP
            if token[0] == "+":
                action, token = SS_DOWN, token[1:].strip()
            elif token[0] == "-":
                action, token = SS_UP, token[1:].strip()

            code = keycodes.NAME_TO_CODE.get(token.upper())
            if code is None:
                raise MacroError(f"unknown keycode '{token}'")
            if code > 0xFF:
                raise MacroError(
                    f"'{token}' does not fit in a macro step "
                    "(macros only take basic keycodes)"
                )
            out += bytes([SS_QMK_PREFIX, action, code])
            continue

        if char == "\n":
            out += bytes([SS_QMK_PREFIX, SS_TAP,
                          keycodes.NAME_TO_CODE["KC_ENT"]])
            i += 1
            continue

        if 32 <= ord(char) <= 126:
            out.append(ord(char))
            i += 1
            continue

        raise MacroError(
            f"character {char!r} cannot be sent literally - "
            "use a {KC_...} step instead"
        )

    if 0 in out:
        raise MacroError("macro body cannot contain a null byte")
    return bytes(out)


def decode_macro(data):
    """Turn raw macro bytes back into the text syntax."""
    out = []
    i = 0
    while i < len(data):
        byte = data[i]

        if byte == SS_QMK_PREFIX and i + 1 < len(data):
            action = data[i + 1]

            if action in (SS_TAP, SS_DOWN, SS_UP) and i + 2 < len(data):
                code = data[i + 2]
                name = keycodes.BASIC.get(code, (f"0x{code:02X}", ""))[0]
                prefix = {SS_TAP: "", SS_DOWN: "+", SS_UP: "-"}[action]
                out.append("{" + prefix + name + "}")
                i += 3
                continue

            if action == SS_DELAY and i + 3 < len(data):
                ms = (data[i + 2] - 1) + (data[i + 3] - 1) * 255
                out.append("{" + str(ms) + "}")
                i += 4
                continue

        if byte == ord("{"):
            out.append("{{")
        elif 32 <= byte <= 126:
            out.append(chr(byte))
        else:
            out.append(f"{{0x{byte:02X}}}")
        i += 1

    return "".join(out)


def split_buffer(buffer, count):
    """Split the raw buffer into `count` macro bodies."""
    bodies = []
    current = bytearray()
    for byte in buffer:
        if len(bodies) >= count:
            break
        if byte == 0:
            bodies.append(bytes(current))
            current = bytearray()
        else:
            current.append(byte)
    while len(bodies) < count:
        bodies.append(b"")
    return bodies


def join_buffer(bodies, size):
    """Pack macro bodies back into a buffer of exactly `size` bytes."""
    out = bytearray()
    for body in bodies:
        out += body + b"\x00"
    if len(out) > size:
        raise MacroError(
            f"macros need {len(out)} bytes but the keyboard only has {size}"
        )
    return bytes(out + b"\x00" * (size - len(out)))
