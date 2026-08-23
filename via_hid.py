"""Minimal VIA raw-HID transport for QMK keyboards on Windows.

No third-party packages: this drives the Win32 HID + SetupAPI DLLs through
ctypes. It finds the vendor-defined HID interface (usage page 0xFF60,
usage 0x61) that QMK exposes when VIA_ENABLE is set, and speaks the VIA
protocol over it.

The device is located by walking the HID interface list rather than by a
hardcoded device path, so replugging into a different USB port is fine.
"""

import ctypes
import re
from ctypes import wintypes

# ---------------------------------------------------------------- constants

VIA_USAGE_PAGE = 0xFF60
VIA_USAGE = 0x61

REPORT_LEN = 32  # VIA payload size; Windows prepends a report-ID byte

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x01
FILE_SHARE_WRITE = 0x02
OPEN_EXISTING = 3
FILE_FLAG_OVERLAPPED = 0x40000000
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

DIGCF_PRESENT = 0x02
DIGCF_DEVICEINTERFACE = 0x10

WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102

# VIA command IDs (protocol 9-12)
CMD_GET_PROTOCOL_VERSION = 0x01
CMD_GET_KEYBOARD_VALUE = 0x02
CMD_SET_KEYBOARD_VALUE = 0x03
CMD_DYNAMIC_KEYMAP_GET_KEYCODE = 0x04
CMD_DYNAMIC_KEYMAP_SET_KEYCODE = 0x05
CMD_DYNAMIC_KEYMAP_RESET = 0x06
CMD_CUSTOM_SET_VALUE = 0x07
CMD_CUSTOM_GET_VALUE = 0x08
CMD_CUSTOM_SAVE = 0x09
CMD_EEPROM_RESET = 0x0A
CMD_BOOTLOADER_JUMP = 0x0B  # never send this by accident
CMD_DYNAMIC_KEYMAP_MACRO_GET_COUNT = 0x0C
CMD_DYNAMIC_KEYMAP_MACRO_GET_BUFFER_SIZE = 0x0D
CMD_DYNAMIC_KEYMAP_MACRO_GET_BUFFER = 0x0E
CMD_DYNAMIC_KEYMAP_MACRO_SET_BUFFER = 0x0F
CMD_DYNAMIC_KEYMAP_MACRO_RESET = 0x10
CMD_DYNAMIC_KEYMAP_GET_LAYER_COUNT = 0x11
CMD_DYNAMIC_KEYMAP_GET_BUFFER = 0x12
CMD_DYNAMIC_KEYMAP_SET_BUFFER = 0x13

# ------------------------------------------------------------- ctypes setup

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
setupapi = ctypes.WinDLL("setupapi", use_last_error=True)
hid = ctypes.WinDLL("hid", use_last_error=True)


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("InterfaceClassGuid", GUID),
        ("Flags", wintypes.DWORD),
        ("Reserved", ctypes.POINTER(ctypes.c_ulong)),
    ]


class HIDD_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Size", wintypes.ULONG),
        ("VendorID", wintypes.USHORT),
        ("ProductID", wintypes.USHORT),
        ("VersionNumber", wintypes.USHORT),
    ]


class HIDP_CAPS(ctypes.Structure):
    _fields_ = [
        ("Usage", wintypes.USHORT),
        ("UsagePage", wintypes.USHORT),
        ("InputReportByteLength", wintypes.USHORT),
        ("OutputReportByteLength", wintypes.USHORT),
        ("FeatureReportByteLength", wintypes.USHORT),
        ("Reserved", wintypes.USHORT * 17),
        ("NumberLinkCollectionNodes", wintypes.USHORT),
        ("NumberInputButtonCaps", wintypes.USHORT),
        ("NumberInputValueCaps", wintypes.USHORT),
        ("NumberInputDataIndices", wintypes.USHORT),
        ("NumberOutputButtonCaps", wintypes.USHORT),
        ("NumberOutputValueCaps", wintypes.USHORT),
        ("NumberOutputDataIndices", wintypes.USHORT),
        ("NumberFeatureButtonCaps", wintypes.USHORT),
        ("NumberFeatureValueCaps", wintypes.USHORT),
        ("NumberFeatureDataIndices", wintypes.USHORT),
    ]


class OVERLAPPED(ctypes.Structure):
    _fields_ = [
        ("Internal", ctypes.c_void_p),
        ("InternalHigh", ctypes.c_void_p),
        ("Offset", wintypes.DWORD),
        ("OffsetHigh", wintypes.DWORD),
        ("hEvent", wintypes.HANDLE),
    ]


kernel32.CreateFileW.restype = wintypes.HANDLE
kernel32.CreateFileW.argtypes = [
    wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
    ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
]
kernel32.CreateEventW.restype = wintypes.HANDLE
kernel32.CreateEventW.argtypes = [
    ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR
]
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.GetOverlappedResult.argtypes = [
    wintypes.HANDLE, ctypes.POINTER(OVERLAPPED),
    ctypes.POINTER(wintypes.DWORD), wintypes.BOOL,
]

kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.ResetEvent.argtypes = [wintypes.HANDLE]
kernel32.CancelIo.argtypes = [wintypes.HANDLE]
kernel32.WriteFile.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(OVERLAPPED),
]
kernel32.ReadFile.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(OVERLAPPED),
]

# HDEVINFO is a pointer: without explicit argtypes ctypes truncates it to
# 32 bits and every call after the first overflows.
setupapi.SetupDiGetClassDevsW.restype = wintypes.HANDLE
setupapi.SetupDiGetClassDevsW.argtypes = [
    ctypes.POINTER(GUID), wintypes.LPCWSTR, wintypes.HWND, wintypes.DWORD
]
setupapi.SetupDiEnumDeviceInterfaces.restype = wintypes.BOOL
setupapi.SetupDiEnumDeviceInterfaces.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, ctypes.POINTER(GUID), wintypes.DWORD,
    ctypes.POINTER(SP_DEVICE_INTERFACE_DATA),
]
setupapi.SetupDiGetDeviceInterfaceDetailW.restype = wintypes.BOOL
setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [
    wintypes.HANDLE, ctypes.POINTER(SP_DEVICE_INTERFACE_DATA),
    ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
    ctypes.c_void_p,
]
setupapi.SetupDiDestroyDeviceInfoList.restype = wintypes.BOOL
setupapi.SetupDiDestroyDeviceInfoList.argtypes = [wintypes.HANDLE]

hid.HidD_GetHidGuid.argtypes = [ctypes.POINTER(GUID)]
hid.HidD_GetAttributes.argtypes = [
    wintypes.HANDLE, ctypes.POINTER(HIDD_ATTRIBUTES)
]
hid.HidD_GetPreparsedData.argtypes = [
    wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p)
]
hid.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]
hid.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.POINTER(HIDP_CAPS)]


class DeviceError(Exception):
    """Raised when the keyboard cannot be found or stops responding."""


# ------------------------------------------------------------- enumeration

def _interface_paths():
    """Yield the device path of every present HID interface."""
    guid = GUID()
    hid.HidD_GetHidGuid(ctypes.byref(guid))

    dev_info = setupapi.SetupDiGetClassDevsW(
        ctypes.byref(guid), None, None, DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
    )
    if dev_info == INVALID_HANDLE_VALUE:
        raise DeviceError("SetupDiGetClassDevs failed")

    try:
        index = 0
        while True:
            iface = SP_DEVICE_INTERFACE_DATA()
            iface.cbSize = ctypes.sizeof(SP_DEVICE_INTERFACE_DATA)
            if not setupapi.SetupDiEnumDeviceInterfaces(
                dev_info, None, ctypes.byref(guid), index, ctypes.byref(iface)
            ):
                break
            index += 1

            needed = wintypes.DWORD(0)
            setupapi.SetupDiGetDeviceInterfaceDetailW(
                dev_info, ctypes.byref(iface), None, 0,
                ctypes.byref(needed), None,
            )
            if not needed.value:
                continue

            buf = ctypes.create_string_buffer(needed.value)
            # cbSize of SP_DEVICE_INTERFACE_DETAIL_DATA_W: 8 on 64-bit, 6 on 32-bit
            cb = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
            ctypes.memmove(buf, ctypes.byref(wintypes.DWORD(cb)), 4)

            if setupapi.SetupDiGetDeviceInterfaceDetailW(
                dev_info, ctypes.byref(iface), buf, needed.value,
                ctypes.byref(needed), None,
            ):
                yield ctypes.wstring_at(ctypes.addressof(buf) + 4)
    finally:
        setupapi.SetupDiDestroyDeviceInfoList(dev_info)


ERROR_SHARING_VIOLATION = 32


def _open(path, exclusive=False):
    """Open a HID interface.

    Enumeration uses shared mode so probing never disturbs another app.
    An actual session opens exclusively: two clients on one VIA interface
    interleave their requests and each can read the other's reply, which
    silently returns wrong data rather than failing.
    """
    share = 0 if exclusive else (FILE_SHARE_READ | FILE_SHARE_WRITE)
    return kernel32.CreateFileW(
        path,
        GENERIC_READ | GENERIC_WRITE,
        share,
        None,
        OPEN_EXISTING,
        FILE_FLAG_OVERLAPPED,
        None,
    )


def _describe(handle):
    """Return (vid, pid, usage_page, usage) for an open HID handle."""
    attrs = HIDD_ATTRIBUTES()
    attrs.Size = ctypes.sizeof(HIDD_ATTRIBUTES)
    if not hid.HidD_GetAttributes(handle, ctypes.byref(attrs)):
        return None

    preparsed = ctypes.c_void_p()
    if not hid.HidD_GetPreparsedData(handle, ctypes.byref(preparsed)):
        return None
    try:
        caps = HIDP_CAPS()
        hid.HidP_GetCaps(preparsed, ctypes.byref(caps))
        return attrs.VendorID, attrs.ProductID, caps.UsagePage, caps.Usage
    finally:
        hid.HidD_FreePreparsedData(preparsed)


_PATH_IDS = re.compile(r"vid_([0-9a-f]{4})&pid_([0-9a-f]{4})", re.IGNORECASE)


def _ids_from_path(path):
    """(vid, pid) parsed out of a device path, or (None, None)."""
    match = _PATH_IDS.search(path)
    if not match:
        return (None, None)
    return (int(match.group(1), 16), int(match.group(2), 16))


def find_devices(include_busy=False):
    """List every VIA-capable HID interface as (vid, pid, path) tuples.

    With include_busy, returns (found, busy) instead, where busy holds
    (vid, pid, path) for interfaces that exist but are already held
    exclusively by someone else. That distinction matters: an interface
    another program has open looks exactly like an absent keyboard here,
    because we cannot open it to ask what it is, and "no keyboard found" is
    the wrong thing to tell the user when the keyboard is sitting right
    there with VIA attached to it.

    A busy interface cannot be queried, so its vid/pid are read out of the
    device path instead - plenty of unrelated HID devices are held open by
    the system, and the caller needs to tell them apart from the keyboard.
    """
    found, busy = [], []
    for path in _interface_paths():
        handle = _open(path)
        if handle == INVALID_HANDLE_VALUE:
            # ERROR_ACCESS_DENIED is normal: Windows protects the plain
            # keyboard interfaces. A sharing violation is another program.
            if ctypes.get_last_error() == ERROR_SHARING_VIOLATION:
                busy.append(_ids_from_path(path) + (path,))
            continue
        try:
            info = _describe(handle)
            if info and info[2] == VIA_USAGE_PAGE and info[3] == VIA_USAGE:
                found.append((info[0], info[1], path))
        finally:
            kernel32.CloseHandle(handle)
    return (found, busy) if include_busy else found


# ------------------------------------------------------------------ device

class ViaDevice:
    """An open VIA raw-HID channel to one keyboard."""

    def __init__(self, path, timeout_ms=1000):
        self.path = path
        self.timeout_ms = timeout_ms
        self._handle = _open(path, exclusive=True)
        if self._handle == INVALID_HANDLE_VALUE:
            error = ctypes.get_last_error()
            if error == ERROR_SHARING_VIOLATION:
                raise DeviceError(
                    "Another program is already using this keyboard. Close "
                    "the other Split70 Configurator window (or VIA / the "
                    "Epomaker Hub) and try again."
                )
            raise DeviceError(
                f"Could not open the keyboard (win32 error {error})."
            )
        self._event = kernel32.CreateEventW(None, True, False, None)

    # -- lifecycle ---------------------------------------------------------

    def close(self):
        if self._handle and self._handle != INVALID_HANDLE_VALUE:
            kernel32.CloseHandle(self._handle)
            self._handle = None
        if self._event:
            kernel32.CloseHandle(self._event)
            self._event = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # -- transport ---------------------------------------------------------

    def _wait(self, ov):
        """Block on an overlapped op; returns bytes transferred or raises."""
        rc = kernel32.WaitForSingleObject(self._event, self.timeout_ms)
        if rc == WAIT_TIMEOUT:
            kernel32.CancelIo(self._handle)
            raise DeviceError("Keyboard did not respond (timed out).")
        moved = wintypes.DWORD(0)
        if not kernel32.GetOverlappedResult(
            self._handle, ctypes.byref(ov), ctypes.byref(moved), False
        ):
            raise DeviceError(
                "HID transfer failed (win32 error "
                f"{ctypes.get_last_error()})"
            )
        return moved.value

    def transact(self, payload):
        """Send a VIA command and return the 32-byte response payload."""
        if len(payload) > REPORT_LEN:
            raise ValueError("payload longer than one VIA report")

        # 0xFF is VIA's conventional padding
        out = bytearray([0x00]) + bytearray(payload)
        out += bytes([0xFF] * (REPORT_LEN + 1 - len(out)))

        ov = OVERLAPPED()
        ov.hEvent = self._event
        kernel32.ResetEvent(self._event)
        buf = (ctypes.c_char * len(out)).from_buffer_copy(bytes(out))
        written = wintypes.DWORD(0)
        if not kernel32.WriteFile(
            self._handle, buf, len(out), ctypes.byref(written), ctypes.byref(ov)
        ):
            if ctypes.get_last_error() != 997:  # ERROR_IO_PENDING
                raise DeviceError(
                    f"write failed (win32 error {ctypes.get_last_error()})"
                )
            self._wait(ov)

        ov = OVERLAPPED()
        ov.hEvent = self._event
        kernel32.ResetEvent(self._event)
        rbuf = ctypes.create_string_buffer(REPORT_LEN + 1)
        read = wintypes.DWORD(0)
        if not kernel32.ReadFile(
            self._handle, rbuf, REPORT_LEN + 1, ctypes.byref(read),
            ctypes.byref(ov),
        ):
            if ctypes.get_last_error() != 997:
                raise DeviceError(
                    f"read failed (win32 error {ctypes.get_last_error()})"
                )
            self._wait(ov)

        return rbuf.raw[1:REPORT_LEN + 1]

    # -- VIA protocol ------------------------------------------------------

    def protocol_version(self):
        r = self.transact([CMD_GET_PROTOCOL_VERSION])
        return (r[1] << 8) | r[2]

    def layer_count(self):
        return self.transact([CMD_DYNAMIC_KEYMAP_GET_LAYER_COUNT])[1]

    def get_keycode(self, layer, row, col):
        r = self.transact([CMD_DYNAMIC_KEYMAP_GET_KEYCODE, layer, row, col])
        return (r[4] << 8) | r[5]

    def set_keycode(self, layer, row, col, keycode):
        self.transact([
            CMD_DYNAMIC_KEYMAP_SET_KEYCODE, layer, row, col,
            (keycode >> 8) & 0xFF, keycode & 0xFF,
        ])

    def read_keymap(self, layers, rows, cols):
        """Bulk-read the whole keymap. Returns keymap[layer][row][col]."""
        total = layers * rows * cols * 2  # bytes; keycodes are big-endian u16
        raw = bytearray()
        offset = 0
        chunk = 28  # bytes per GET_BUFFER reply
        while offset < total:
            size = min(chunk, total - offset)
            r = self.transact([
                CMD_DYNAMIC_KEYMAP_GET_BUFFER,
                (offset >> 8) & 0xFF, offset & 0xFF, size,
            ])
            raw += r[4:4 + size]
            offset += size

        keymap = []
        i = 0
        for _ in range(layers):
            layer = []
            for _ in range(rows):
                line = []
                for _ in range(cols):
                    line.append((raw[i] << 8) | raw[i + 1])
                    i += 2
                layer.append(line)
            keymap.append(layer)
        return keymap

    # -- macros ------------------------------------------------------------

    def macro_count(self):
        """How many macro slots the firmware exposes."""
        return self.transact([CMD_DYNAMIC_KEYMAP_MACRO_GET_COUNT])[1]

    def macro_buffer_size(self):
        """Total bytes available for all macros combined."""
        r = self.transact([CMD_DYNAMIC_KEYMAP_MACRO_GET_BUFFER_SIZE])
        return (r[1] << 8) | r[2]

    def read_macro_buffer(self, size=None):
        """Read the whole macro buffer as raw bytes."""
        size = size or self.macro_buffer_size()
        out = bytearray()
        offset = 0
        chunk = 28  # bytes of payload per reply
        while offset < size:
            count = min(chunk, size - offset)
            r = self.transact([
                CMD_DYNAMIC_KEYMAP_MACRO_GET_BUFFER,
                (offset >> 8) & 0xFF, offset & 0xFF, count,
            ])
            out += r[4:4 + count]
            offset += count
        return bytes(out)

    def write_macro_buffer(self, data):
        """Write the whole macro buffer back to the keyboard."""
        offset = 0
        chunk = 28
        while offset < len(data):
            count = min(chunk, len(data) - offset)
            self.transact(
                [CMD_DYNAMIC_KEYMAP_MACRO_SET_BUFFER,
                 (offset >> 8) & 0xFF, offset & 0xFF, count]
                + list(data[offset:offset + count])
            )
            offset += count

    def keymap_reset(self):
        """Put every layer back to the firmware's built-in keymap.

        This is CMD_DYNAMIC_KEYMAP_RESET (0x06). It rewrites the dynamic
        keymap in EEPROM from the defaults compiled into the firmware, so
        every remap is lost. It is NOT the same as CMD_EEPROM_RESET (0x0A),
        which this module deliberately never sends: that wipes everything,
        wireless config included.
        """
        self.transact([CMD_DYNAMIC_KEYMAP_RESET])

    def macro_reset(self):
        """Clear every macro slot."""
        self.transact([CMD_DYNAMIC_KEYMAP_MACRO_RESET])

    # -- custom (lighting) channel ----------------------------------------

    def custom_get(self, channel, value_id, count=1):
        r = self.transact([CMD_CUSTOM_GET_VALUE, channel, value_id])
        return list(r[3:3 + count])

    def custom_set(self, channel, value_id, data):
        self.transact([CMD_CUSTOM_SET_VALUE, channel, value_id] + list(data))

    def custom_save(self, channel):
        self.transact([CMD_CUSTOM_SAVE, channel])
