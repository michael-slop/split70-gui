"""Split70 Configurator -- a small, hackable VIA client with a Tk GUI.

Renders the physical layout straight from a VIA definition JSON, reads the
live keymap out of the keyboard, and writes remaps back over raw HID.
Lighting is driven through VIA's custom-value channel.

Run:  python app.py [path-to-definition.json]
"""

import json
import os
import sys
import colorsys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser

import keycodes
import macrolang
import macros
import via_hid

# ---------------------------------------------------------------- appearance

KEY_UNIT = 52          # pixels per 1u keycap
KEY_PAD = 3            # gap between caps
BG = "#1e1f22"
KEY_FILL = "#2f3238"
KEY_EDGE = "#4a4f57"
KEY_TEXT = "#e6e6e6"
KEY_HOVER = "#3d5a80"
KEY_DIRTY = "#3f6d4e"   # briefly flashed after a successful write
ACCENT = "#7aa2f7"

DEFAULT_DEFINITIONS = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "Epomaker_Split70.json"),
    os.path.expanduser(
        "~/Downloads/Epomaker_Split70/Epomaker_Split70.json"),
]

LIGHTING_CHANNEL = 3    # from the definition: content = [id, channel, value]


# ------------------------------------------------------------------ helpers

def parse_kle(rows):
    """Turn a VIA/KLE layout into [(row, col, x, y, w, h), ...] in key units."""
    keys = []
    y = 0.0
    w = h = 1.0
    for row in rows:
        x = 0.0
        for item in row:
            if isinstance(item, dict):
                x += item.get("x", 0)
                y += item.get("y", 0)
                if "w" in item:
                    w = item["w"]
                if "h" in item:
                    h = item["h"]
                continue
            label = item.split("\n")[0]
            if "," in label:
                r, c = label.split(",")[:2]
                try:
                    keys.append((int(r), int(c), x, y, w, h))
                except ValueError:
                    pass
            x += w
            w = h = 1.0
        y += 1.0
    return keys


def find_menu_item(menus, content_id):
    """Depth-first search of the definition's menus for one control."""
    stack = list(menus)
    while stack:
        node = stack.pop()
        if isinstance(node, list):
            stack.extend(node)
        elif isinstance(node, dict):
            content = node.get("content")
            if isinstance(content, list) and content and isinstance(
                content[0], str
            ):
                if content[0] == content_id:
                    return node
            elif isinstance(content, list):
                stack.extend(content)
    return None


def load_definition(path=None):
    candidates = [path] if path else DEFAULT_DEFINITIONS
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            with open(candidate, encoding="utf-8") as handle:
                return json.load(handle), candidate
    return None, None


# ---------------------------------------------------------------- key picker

class KeycodePicker(tk.Toplevel):
    """Searchable list of every keycode we know how to write."""

    def __init__(self, parent, items, current):
        super().__init__(parent)
        self.title("Choose a keycode")
        self.transient(parent)
        self.resizable(False, True)
        self.result = None
        self.items = items

        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="both", expand=True)

        description = keycodes.describe(current)
        heading = f"Currently: {current}"
        if description:
            heading += f"   ({description})"
        ttk.Label(frame, text=heading).pack(anchor="w")

        self.query = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=self.query, width=38)
        entry.pack(fill="x", pady=(8, 6))
        entry.focus_set()
        self.query.trace_add("write", lambda *_: self.refilter())

        self.listbox = tk.Listbox(frame, height=16, width=46,
                                  activestyle="none",
                                  font=("Consolas", 9))
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<Double-Button-1>", lambda _e: self.accept())

        entry.bind("<Down>", lambda _e: self.listbox.focus_set())
        entry.bind("<Return>", lambda _e: self.accept())
        self.listbox.bind("<Return>", lambda _e: self.accept())
        self.bind("<Escape>", lambda _e: self.destroy())

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text="Set", command=self.accept).pack(side="right")
        ttk.Button(buttons, text="Cancel",
                   command=self.destroy).pack(side="right", padx=6)

        self.refilter()
        self.grab_set()

    def refilter(self):
        needle = self.query.get().strip().upper()
        self.filtered = []
        self.listbox.delete(0, tk.END)
        for name, _label in self.items:
            description = keycodes.describe(name)
            shown = f"{name:<12}  {description}" if description else name
            if needle and needle not in shown.upper():
                continue
            self.filtered.append(name)
            self.listbox.insert(tk.END, shown)
        if self.filtered:
            self.listbox.selection_set(0)

    def accept(self):
        typed = self.query.get().strip()
        selection = self.listbox.curselection()
        if selection:
            self.result = self.filtered[selection[0]]
        elif typed:
            self.result = typed
        self.destroy()


# ----------------------------------------------------------- macro editor

MACRO_HELP_RAW = (
    "Type text to send it literally.   {KC_ENT} taps a key.   "
    "{+KC_LSFT} holds, {-KC_LSFT} releases.\n"
    "{250} waits 250 ms.   {{ is a literal brace.   "
    "Assign a slot to a key with MACRO(0), MACRO(1), ..."
)

MACRO_HELP_SIMPLE = (
    "One step per line:   press win+shift+s    tap enter    hold shift    "
    "release shift\n"
    "type some text    wait 250    # comment.   A bare chord like ctrl+c "
    "means press.  Assign with MACRO(0)."
)


class MacroEditor(tk.Toplevel):
    """Edit the keyboard's macro slots."""

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Macros")
        self.transient(app)
        self.current = 0
        self.bodies = list(app.macro_bodies)

        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="both", expand=True)

        self.mode = tk.StringVar(value="simple")
        self.help_text = tk.StringVar(value=MACRO_HELP_SIMPLE)

        modes = ttk.Frame(frame)
        modes.grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(modes, text="Editing style:").pack(side="left")
        for label, value in (("Plain English", "simple"), ("Raw", "raw")):
            ttk.Radiobutton(modes, text=label, value=value,
                            variable=self.mode,
                            command=self.on_mode_change).pack(side="left",
                                                              padx=(8, 0))

        ttk.Label(frame, textvariable=self.help_text, justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(6, 10))

        self.listbox = tk.Listbox(frame, width=30, height=16,
                                  activestyle="none", exportselection=False)
        self.listbox.grid(row=2, column=0, sticky="ns")
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        right = ttk.Frame(frame)
        right.grid(row=2, column=1, sticky="nsew", padx=(10, 0))
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(2, weight=1)

        self.editor = tk.Text(right, width=52, height=11, wrap="word",
                              font=("Consolas", 10))
        self.editor.pack(fill="both", expand=True)
        self.editor.bind("<KeyRelease>", lambda _e: self.update_preview())

        ttk.Label(right, text="What it will do:").pack(anchor="w",
                                                       pady=(8, 2))
        self.preview_box = tk.Text(right, width=52, height=6, wrap="word",
                                   font=("Consolas", 9), state="disabled",
                                   background="#f4f4f4", relief="flat")
        self.preview_box.pack(fill="x")

        buttons = ttk.Frame(frame)
        buttons.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        ttk.Button(buttons, text="Write all to keyboard",
                   command=self.write_all).pack(side="right")
        ttk.Button(buttons, text="Reload from keyboard",
                   command=self.reload).pack(side="right", padx=6)
        ttk.Button(buttons, text="Clear this slot",
                   command=self.clear_slot).pack(side="left")

        self.status = tk.StringVar()
        ttk.Label(frame, textvariable=self.status).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

        self.refresh_list()
        self.listbox.selection_set(0)
        self.load_slot(0)
        self.update_usage()

    # -- helpers -----------------------------------------------------------

    def preview(self, index):
        text = macros.decode_macro(self.bodies[index])
        if not text:
            return f"MACRO({index})   (empty)"
        if len(text) > 22:
            text = text[:21] + "…"
        return f"MACRO({index})   {text}"

    def refresh_list(self):
        selection = self.listbox.curselection()
        self.listbox.delete(0, tk.END)
        for index in range(len(self.bodies)):
            self.listbox.insert(tk.END, self.preview(index))
        if selection:
            self.listbox.selection_set(selection[0])

    def to_wire(self, text):
        """Editor contents -> wire syntax, whichever style is showing."""
        if self.mode.get() == "simple":
            return macrolang.compile_script(text)
        return text

    def show_wire(self, wire):
        """Put wire syntax into the editor in the current style."""
        self.editor.delete("1.0", tk.END)
        if self.mode.get() == "simple":
            wire = macrolang.decompile(wire)
        self.editor.insert("1.0", wire)
        self.update_preview()

    def load_slot(self, index):
        self.current = index
        self.show_wire(macros.decode_macro(self.bodies[index]))

    def update_preview(self):
        """Live plain-English description of the macro being edited."""
        try:
            wire = self.to_wire(self.editor.get("1.0", "end-1c"))
            macros.encode_macro(wire)  # surfaces size/keycode problems too
            lines = macrolang.explain(wire)
            body = "\n".join(lines) if lines else "(nothing yet)"
        except (macrolang.ScriptError, macros.MacroError) as exc:
            body = f"! {exc}"
        self.preview_box.configure(state="normal")
        self.preview_box.delete("1.0", tk.END)
        self.preview_box.insert("1.0", body)
        self.preview_box.configure(state="disabled")

    def on_mode_change(self):
        """Convert what is in the editor rather than discarding it."""
        simple = self.mode.get() == "simple"
        self.help_text.set(MACRO_HELP_SIMPLE if simple else MACRO_HELP_RAW)
        text = self.editor.get("1.0", "end-1c")
        try:
            # The text is still in the *previous* style, so compile it with
            # that one before re-rendering in the newly selected style.
            wire = text if simple else macrolang.compile_script(text)
        except macrolang.ScriptError as exc:
            messagebox.showerror("Macro error", str(exc))
            self.mode.set("simple" if not simple else "raw")
            self.help_text.set(MACRO_HELP_RAW if simple
                               else MACRO_HELP_SIMPLE)
            return
        self.show_wire(wire)

    def stash_current(self):
        """Encode the editor contents back into the in-memory slot."""
        try:
            wire = self.to_wire(self.editor.get("1.0", "end-1c"))
            self.bodies[self.current] = macros.encode_macro(wire)
        except (macrolang.ScriptError, macros.MacroError) as exc:
            messagebox.showerror(
                "Macro error", f"MACRO({self.current}): {exc}"
            )
            return False
        self.update_preview()
        return True

    def update_usage(self):
        used = sum(len(b) + 1 for b in self.bodies)
        self.status.set(
            f"{used} of {self.app.macro_size} bytes used across "
            f"{len(self.bodies)} slots"
        )

    # -- actions -----------------------------------------------------------

    def on_select(self, _event=None):
        selection = self.listbox.curselection()
        if not selection or selection[0] == self.current:
            return
        target = selection[0]
        if not self.stash_current():
            # bounce the selection back to the slot that failed to parse
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.current)
            return
        self.refresh_list()
        self.update_usage()
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(target)
        self.load_slot(target)

    def clear_slot(self):
        self.bodies[self.current] = b""
        self.editor.delete("1.0", tk.END)
        self.refresh_list()
        self.update_usage()

    def reload(self):
        if not self.app.device:
            return
        self.app.read_macros()
        self.bodies = list(self.app.macro_bodies)
        self.refresh_list()
        self.load_slot(self.current)
        self.update_usage()
        self.status.set("Reloaded from keyboard.")

    def write_all(self):
        if not self.app.device:
            messagebox.showinfo("Not connected", "No keyboard connected.")
            return
        if not self.stash_current():
            return
        try:
            buffer = macros.join_buffer(self.bodies, self.app.macro_size)
        except macros.MacroError as exc:
            messagebox.showerror("Too big", str(exc))
            return
        try:
            self.app.device.write_macro_buffer(buffer)
        except via_hid.DeviceError as exc:
            messagebox.showerror("Write failed", str(exc))
            return
        self.app.macro_bodies = list(self.bodies)
        self.refresh_list()
        self.update_usage()
        self.app.draw()
        self.status.set("Written to keyboard.")


# ----------------------------------------------------------------- about

ABOUT_SECTIONS = [
    ("Wireless: the keys that matter", [
        "Fn + Q  -  Bluetooth slot 1",
        "Fn + W  -  Bluetooth slot 2",
        "Fn + E  -  Bluetooth slot 3",
        "Fn + R  -  2.4GHz dongle",
        "Hold any of them 3-5 seconds to re-pair.",
        "",
        "These live on layer 1, so they are not",
        "visible on layer 0.",
        "",
        "If wireless seems dead, check these first:",
        "1. Unplug the USB cable. A cable forces",
        "   USB mode regardless of the switch.",
        "2. Check the physical switch position.",
        "3. For 2.4GHz, make sure the dongle is",
        "   plugged into the computer.",
    ]),
    ("Do not remap these", [
        "KC_BT1, KC_BT2, KC_BT3, KC_2G4 are your",
        "only way to reach Bluetooth and 2.4GHz.",
        "Lose them and you are wired-only until you",
        "put them back. This app asks first.",
        "",
        "EE_CLR (Fn + Backspace) erases every remap",
        "back to factory. It is a real key on the",
        "keyboard, not a button in this app.",
    ]),
    ("Layers", [
        "0  -  base typing layer",
        "1  -  Fn layer: function keys, wireless, RGB",
        "2  -  alternate base layer",
        "3  -  alternate Fn layer",
        "",
        "KC_TRNS falls through to the layer below.",
        "KC_NO is a matrix slot with no real key.",
    ]),
    ("Remapping", [
        "Click a key, search, pick. It writes to the",
        "keyboard immediately and survives",
        "unplugging. There is no save button.",
        "",
        "You can also type these into the search box:",
        "MO(1)         hold for layer 1",
        "TG(2)         toggle layer 2",
        "LT(1,KC_SPC)  tap Space, hold for layer 1",
        "MACRO(0)      run macro slot 0",
        "0x00A8        any raw keycode",
    ]),
    ("Shortcuts on one key", [
        "A modifier plus a key fits in a single",
        "keycode - no macro slot needed:",
        "",
        "LCTL(KC_C)          Ctrl+C",
        "LGUI(KC_L)          Win+L, locks the PC",
        "LALT(KC_F4)         close window",
        "LCTL(LSFT(KC_ESC))  Task Manager",
        "LGUI(LSFT(KC_S))    screenshot snip",
        "",
        "Search the picker for copy, paste, lock,",
        "Task Manager and so on - common ones are",
        "listed. Or type any LCTL(...) / LSFT(...) /",
        "LALT(...) / LGUI(...) combination yourself.",
        "",
        "Use a macro instead when you need a",
        "sequence, a delay, or literal text.",
    ]),
    ("Macros", [
        "hello       types hello",
        "{KC_ENT}    taps Enter",
        "{+KC_LSFT}  holds Shift",
        "{-KC_LSFT}  releases Shift",
        "{250}       waits 250 ms",
        "{{          a literal brace",
        "",
        "Assign one to a key as MACRO(0)..MACRO(15).",
        "Macro steps take basic keycodes only, so",
        "MO(1) cannot go inside a macro.",
    ]),
    ("Connection", [
        "This app only works over the USB cable. The",
        "raw-HID interface it uses does not exist in",
        "Bluetooth or 2.4GHz mode.",
        "",
        "One client at a time. Two programs sharing",
        "the interface can read each other's replies",
        "and silently get wrong data, so this app",
        "opens it exclusively. Close VIA or the",
        "Epomaker Hub first.",
    ]),
]


class AboutWindow(tk.Toplevel):
    """Everything worth knowing that is not obvious from the layout."""

    def __init__(self, app):
        super().__init__(app)
        self.title("About / Help")
        self.transient(app)

        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="both", expand=True)

        # wrap="word", not "none": a tiling window manager decides how wide
        # this ends up, and clipped help text is worse than useless.
        text = tk.Text(frame, width=48, height=30, wrap="word",
                       font=("Consolas", 9), padx=8, pady=8)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        text.tag_configure("h", font=("Segoe UI", 11, "bold"),
                           spacing1=10, spacing3=6)
        text.tag_configure("warn", foreground="#b5482f")

        device = (
            f"{app.definition.get('name', 'keyboard')}   "
            f"{app.layers} layers   {app.macro_count} macro slots   "
            f"{app.macro_size} macro bytes"
        ) if app.device else "Not connected - plug the keyboard in by USB."
        text.insert(tk.END, "Split70 Configurator\n", "h")
        text.insert(tk.END, device + "\n")
        text.insert(tk.END, f"Files: {os.path.dirname(os.path.abspath(__file__))}\n")

        for heading, lines in ABOUT_SECTIONS:
            text.insert(tk.END, "\n" + heading + "\n", "h")
            for line in lines:
                tag = "warn" if heading == "Do not remap these" else ""
                text.insert(tk.END, line + "\n", tag)

        text.configure(state="disabled")

        ttk.Button(self, text="Close", command=self.destroy).pack(
            pady=(0, 10))


# ------------------------------------------------------------------- the app

class App(tk.Tk):
    def __init__(self, definition_path=None):
        super().__init__()
        self.title("Split70 Configurator")
        self.configure(bg=BG)

        self.device = None
        self.keymap = []
        self.layer = 0
        self.layers = 4
        self.rows = 10
        self.cols = 9
        self.keys = []
        self.rects = {}
        self.macro_count = 0
        self.macro_size = 0
        self.macro_bodies = []

        self.definition, self.definition_path = load_definition(definition_path)
        if not self.definition:
            chosen = filedialog.askopenfilename(
                title="Select the VIA definition JSON",
                filetypes=[("VIA definition", "*.json"), ("All files", "*.*")],
            )
            self.definition, self.definition_path = load_definition(chosen)
        if not self.definition:
            messagebox.showerror(
                "No definition",
                "A VIA definition JSON is required to draw the layout.",
            )
            self.destroy()
            return

        matrix = self.definition.get("matrix", {})
        self.rows = matrix.get("rows", 10)
        self.cols = matrix.get("cols", 9)
        self.custom = self.definition.get("customKeycodes", [])
        self.keys = parse_kle(self.definition["layouts"]["keymap"])
        self.extent_x = max(
            (x + w for _r, _c, x, _y, w, _h in self.keys), default=15.0)
        self.extent_y = max(
            (y + h for _r, _c, _x, y, _w, h in self.keys), default=5.0)
        self._last_size = (0, 0)
        self._loading = False

        self._build_ui()
        self.after(120, self.connect)

    # -- construction ------------------------------------------------------

    def _build_ui(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        bar = ttk.Frame(self, padding=(10, 8))
        bar.pack(fill="x")

        self.status = tk.StringVar(value="Looking for keyboard...")
        ttk.Label(bar, textvariable=self.status).pack(side="left")

        ttk.Button(bar, text="Reconnect",
                   command=self.connect).pack(side="right")
        ttk.Button(bar, text="Reload keymap",
                   command=self.refresh_keymap).pack(side="right", padx=6)
        ttk.Button(bar, text="Macros...",
                   command=self.open_macros).pack(side="right")
        ttk.Button(bar, text="About / Help",
                   command=lambda: AboutWindow(self)).pack(side="right",
                                                           padx=6)

        layer_bar = ttk.Frame(self, padding=(10, 0))
        layer_bar.pack(fill="x")
        ttk.Label(layer_bar, text="Layer").pack(side="left", padx=(0, 8))
        self.layer_buttons = []
        for index in range(self.layers):
            button = ttk.Button(
                layer_bar, text=str(index), width=3,
                command=lambda i=index: self.select_layer(i),
            )
            button.pack(side="left", padx=2)
            self.layer_buttons.append(button)

        width, height = self._canvas_size()
        self.canvas = tk.Canvas(
            self, width=width, height=height, bg=BG,
            highlightthickness=0, bd=0,
        )
        # fill/expand rather than a fixed size: a tiling window manager will
        # hand us whatever tile it likes, and the layout has to cope.
        self.canvas.pack(padx=10, pady=10, fill="both", expand=True)
        self.canvas.bind("<Configure>", self.on_canvas_resize)

        self._build_lighting()

        self.hint = tk.StringVar(
            value="Click any key to remap it. Changes save to the keyboard "
                  "immediately."
        )
        ttk.Label(self, textvariable=self.hint,
                  padding=(10, 0, 10, 10)).pack(anchor="w")

        self.minsize(520, 400)

    def _build_lighting(self):
        box = ttk.LabelFrame(self, text="Lighting", padding=10)
        box.pack(fill="x", padx=10, pady=(0, 10))

        effect_node = find_menu_item(
            self.definition.get("menus", []), "id_qmk_rgb_matrix_effect"
        )
        self.effects = effect_node.get("options", []) if effect_node else []

        ttk.Label(box, text="Effect").grid(row=0, column=0, sticky="w")
        self.effect_choice = ttk.Combobox(
            box, state="readonly", width=28,
            values=[str(option[0]) for option in self.effects],
        )
        self.effect_choice.grid(row=0, column=1, sticky="w", padx=8)
        self.effect_choice.bind("<<ComboboxSelected>>", self.on_effect)

        ttk.Label(box, text="Brightness").grid(row=1, column=0, sticky="w",
                                               pady=(8, 0))
        self.brightness = tk.IntVar(value=128)
        ttk.Scale(box, from_=0, to=255, variable=self.brightness,
                  command=lambda _v: self.on_light(1, self.brightness),
                  length=240).grid(row=1, column=1, sticky="w", padx=8,
                                   pady=(8, 0))

        ttk.Label(box, text="Speed").grid(row=2, column=0, sticky="w",
                                          pady=(8, 0))
        self.speed = tk.IntVar(value=128)
        ttk.Scale(box, from_=0, to=255, variable=self.speed,
                  command=lambda _v: self.on_light(3, self.speed),
                  length=240).grid(row=2, column=1, sticky="w", padx=8,
                                   pady=(8, 0))

        ttk.Button(box, text="Colour...",
                   command=self.on_colour).grid(row=3, column=1, sticky="w",
                                                padx=8, pady=(10, 0))
        ttk.Button(box, text="Save lighting to keyboard",
                   command=self.on_save_lighting).grid(row=3, column=1,
                                                       sticky="e", padx=8,
                                                       pady=(10, 0))

    def _canvas_size(self):
        return (int(self.extent_x * KEY_UNIT) + 20,
                int(self.extent_y * KEY_UNIT) + 20)

    def on_canvas_resize(self, event):
        """Rescale the keycaps whenever the window changes size."""
        if (event.width, event.height) == self._last_size:
            return
        self._last_size = (event.width, event.height)
        self.draw()

    def _unit(self):
        """Pixels per 1u that make the whole board fit the current canvas."""
        width = self.canvas.winfo_width() or self._canvas_size()[0]
        height = self.canvas.winfo_height() or self._canvas_size()[1]
        return max(16, min((width - 8) / self.extent_x,
                           (height - 8) / self.extent_y))

    # -- device ------------------------------------------------------------

    def connect(self):
        if self.device:
            self.device.close()
            self.device = None
        try:
            found, busy = via_hid.find_devices(include_busy=True)
        except via_hid.DeviceError as exc:
            self.status.set(f"Enumeration failed: {exc}")
            return

        if not found:
            # Plenty of unrelated HID devices are held open by the system;
            # only complain about a busy interface that is this keyboard.
            wanted = self.definition.get("vendorId") if self.definition else None
            wanted = int(wanted, 16) if isinstance(wanted, str) else wanted
            busy = [b for b in busy
                    if b[0] is not None and (wanted is None or b[0] == wanted)]
            if busy:
                self.status.set(
                    "Keyboard is there but in use - close the other "
                    "Split70 Configurator window, VIA, or the Epomaker Hub."
                )
            else:
                self.status.set(
                    "No VIA interface found - plug in by USB (VIA does not "
                    "work over Bluetooth or the 2.4GHz dongle)."
                )
            self.draw()
            return

        vid, pid, path = found[0]
        try:
            self.device = via_hid.ViaDevice(path)
            version = self.device.protocol_version()
            self.layers = self.device.layer_count() or 4
        except via_hid.DeviceError as exc:
            self.status.set(str(exc))
            self.device = None
            self.draw()
            return

        self.status.set(
            f"Connected  {vid:04X}:{pid:04X}   VIA protocol {version}   "
            f"{self.layers} layers"
        )
        self.refresh_keymap()
        self.read_macros()
        self.read_lighting()

    def refresh_keymap(self):
        if not self.device:
            self.draw()
            return
        try:
            self.keymap = self.device.read_keymap(
                self.layers, self.rows, self.cols
            )
        except via_hid.DeviceError as exc:
            self.status.set(f"Read failed: {exc}")
        self.draw()

    def read_macros(self):
        """Pull the macro slots off the keyboard."""
        if not self.device:
            return
        try:
            self.macro_count = self.device.macro_count()
            self.macro_size = self.device.macro_buffer_size()
            buffer = self.device.read_macro_buffer(self.macro_size)
            self.macro_bodies = macros.split_buffer(buffer, self.macro_count)
        except via_hid.DeviceError as exc:
            self.status.set(f"Macro read failed: {exc}")

    def open_macros(self):
        if not self.device:
            messagebox.showinfo("Not connected", "No keyboard connected.")
            return
        if not self.macro_count:
            self.read_macros()
        MacroEditor(self)

    def read_lighting(self):
        """Populate the lighting controls. Must not write anything back."""
        if not self.device:
            return
        # Setting the Tk variables fires the Scale callbacks, which would
        # otherwise echo every value straight back at the keyboard.
        self._loading = True
        try:
            self.brightness.set(
                self.device.custom_get(LIGHTING_CHANNEL, 1)[0]
            )
            effect = self.device.custom_get(LIGHTING_CHANNEL, 2)[0]
            self.speed.set(self.device.custom_get(LIGHTING_CHANNEL, 3)[0])
            for index, option in enumerate(self.effects):
                if option[1] == effect:
                    self.effect_choice.current(index)
                    break
        except (via_hid.DeviceError, IndexError):
            pass  # lighting is optional; never block the keymap on it
        finally:
            self._loading = False

    # -- drawing -----------------------------------------------------------

    def select_layer(self, index):
        self.layer = index
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        self.rects.clear()

        for index, button in enumerate(self.layer_buttons):
            button.state(["pressed"] if index == self.layer else ["!pressed"])

        unit = self._unit()
        pad = max(1.0, KEY_PAD * unit / KEY_UNIT)

        # centre the board in whatever space the window manager gave us
        off_x = max(4.0, (self.canvas.winfo_width()
                          - self.extent_x * unit) / 2)
        off_y = max(4.0, (self.canvas.winfo_height()
                          - self.extent_y * unit) / 2)

        for row, col, x, y, w, h in self.keys:
            x0 = x * unit + off_x + pad
            y0 = y * unit + off_y + pad
            x1 = (x + w) * unit + off_x - pad
            y1 = (y + h) * unit + off_y - pad

            keycode = self._keycode(row, col)
            name, label = keycodes.decode(keycode, self.custom)
            if not label:
                label = name.replace("KC_", "")

            rect = self.canvas.create_rectangle(
                x0, y0, x1, y1, fill=KEY_FILL, outline=KEY_EDGE, width=1,
            )
            scale = unit / KEY_UNIT
            size = max(6, int((10 if len(label) <= 5 else 8) * scale))
            text = self.canvas.create_text(
                (x0 + x1) / 2, (y0 + y1) / 2, text=label,
                fill=KEY_TEXT, font=("Segoe UI", size),
            )
            for item in (rect, text):
                self.canvas.tag_bind(
                    item, "<Button-1>",
                    lambda _e, r=row, c=col: self.on_key_click(r, c),
                )
                self.canvas.tag_bind(
                    item, "<Enter>",
                    lambda _e, r=rect, rr=row, cc=col: self.on_hover(r, rr, cc),
                )
                self.canvas.tag_bind(
                    item, "<Leave>",
                    lambda _e, r=rect: self.canvas.itemconfig(r, fill=KEY_FILL),
                )
            self.rects[(row, col)] = rect

    def on_hover(self, rect, row, col):
        self.canvas.itemconfig(rect, fill=KEY_HOVER)
        keycode = self._keycode(row, col)
        name, _ = keycodes.decode(keycode, self.custom)
        text = (f"matrix {row},{col}   layer {self.layer}   {name}   "
                f"(0x{keycode:04X})")
        description = keycodes.describe(name)
        if description:
            text += f"   -   {description}"
        self.hint.set(text)

    def _keycode(self, row, col):
        try:
            return self.keymap[self.layer][row][col]
        except (IndexError, TypeError):
            return 0

    # -- actions -----------------------------------------------------------

    def on_key_click(self, row, col):
        if not self.device:
            messagebox.showinfo("Not connected", "No keyboard connected.")
            return

        current, _ = keycodes.decode(self._keycode(row, col), self.custom)

        if current in keycodes.PROTECTED:
            warning = "\n\n".join([
                f"{current} is currently on this key.",
                keycodes.PROTECTED[current],
                "Remap it anyway?",
            ])
            if not messagebox.askyesno(
                "Remap this key?", warning,
                icon="warning", default="no",
            ):
                return

        picker = KeycodePicker(
            self,
            keycodes.catalog(self.custom, self.layers, self.macro_count),
            current,
        )
        self.wait_window(picker)
        if not picker.result:
            return

        value = keycodes.encode(picker.result, self.custom, self.layers)
        if value is None:
            messagebox.showerror(
                "Unknown keycode",
                f"Could not parse '{picker.result}'.\n\n"
                "Try a KC_* name, MO(1), LT(1,KC_SPC), or a raw 0x1234.",
            )
            return

        try:
            self.device.set_keycode(self.layer, row, col, value)
            self.keymap[self.layer][row][col] = value
        except via_hid.DeviceError as exc:
            messagebox.showerror("Write failed", str(exc))
            return

        self.draw()
        rect = self.rects.get((row, col))
        if rect:
            self.canvas.itemconfig(rect, fill=KEY_DIRTY)
            self.after(350, lambda: self.canvas.itemconfig(rect, fill=KEY_FILL))
        self.status.set(f"Set {row},{col} on layer {self.layer} -> "
                        f"{picker.result}")

    def on_light(self, value_id, variable):
        if not self.device or self._loading:
            return
        try:
            self.device.custom_set(LIGHTING_CHANNEL, value_id,
                                   [int(variable.get()) & 0xFF])
        except via_hid.DeviceError as exc:
            self.status.set(f"Lighting write failed: {exc}")

    def on_effect(self, _event=None):
        if not self.device or self._loading:
            return
        index = self.effect_choice.current()
        if index < 0 or index >= len(self.effects):
            return
        try:
            self.device.custom_set(LIGHTING_CHANNEL, 2,
                                   [int(self.effects[index][1]) & 0xFF])
        except via_hid.DeviceError as exc:
            self.status.set(f"Effect write failed: {exc}")

    def on_colour(self):
        if not self.device or self._loading:
            return
        rgb, _hex = colorchooser.askcolor(title="Pick an RGB colour")
        if not rgb:
            return
        r, g, b = (channel / 255.0 for channel in rgb)
        hue, sat, _val = colorsys.rgb_to_hsv(r, g, b)
        try:
            self.device.custom_set(
                LIGHTING_CHANNEL, 4,
                [int(hue * 255) & 0xFF, int(sat * 255) & 0xFF],
            )
        except via_hid.DeviceError as exc:
            self.status.set(f"Colour write failed: {exc}")

    def on_save_lighting(self):
        if not self.device:
            return
        try:
            self.device.custom_save(LIGHTING_CHANNEL)
            self.status.set("Lighting saved to keyboard.")
        except via_hid.DeviceError as exc:
            self.status.set(f"Save failed: {exc}")

    def destroy(self):
        if self.device:
            self.device.close()
        super().destroy()


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    App(path).mainloop()


if __name__ == "__main__":
    main()
