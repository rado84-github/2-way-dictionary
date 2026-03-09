#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# v0.0.2

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Pango
import os

APP_TITLE = "GTK3 2-Way Dictionary"
WINDOW_WIDTH = 650
WINDOW_HEIGHT = 480

ENTRY_WIDTH = 320
ENTRY_HEIGHT = 40

LEFT_WIDTH = 160
LEFT_HEIGHT = 530

RIGHT_WIDTH = 500
RIGHT_HEIGHT = 530

DICT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dicts")
EN_BG_PATH = os.path.join(DICT_DIR, "en-bg.dat")
BG_EN_PATH = os.path.join(DICT_DIR, "bg-en.dat")

def load_kbg_dat(path):
    with open(path, "rb") as f:
        data = f.read()

    entries = {}
    parts = data.split(b"\x00")

    mapping = {
        "\xa1": "æ",
        "\xa3": "ɔ",
        "\xa4": "ŋ",
        "\xa5": "θ",
        "\xa6": "ʃ",
        "\xa7": "ʊ",
        "\xa8": "ɛ",
        "\xa9": "ʒ",
        "\xad": "ð",
        "Ў": "æ",
        "ў": "ə",
        "¥": "θ",
    }

    trans_table = str.maketrans(mapping)

    for part in parts:
        if not part:
            continue

        try:
            text = part.decode("utf-8")
        except:
            # Тук накрая се прилага таблицата и се прави подмяната на съответните символи
            text = part.decode("cp1251", errors="ignore").translate(trans_table)

        if "\n" not in text:
            continue

        word, translation = text.split("\n", 1)
        word = word.strip()
        translation = translation.strip()

        if not word:
            continue

        entries[word] = translation

    return entries

CONF_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dict.conf")

def is_cyrillic(text: str) -> bool:
    return any("\u0400" <= ch <= "\u04FF" for ch in text)

def load_font_from_conf():
    if not os.path.exists(CONF_PATH):
        return None
    try:
        with open(CONF_PATH, "r", encoding="utf-8") as f:
            line = f.readline().strip()
            if line:
                return line
    except Exception:
        pass
    return None

def save_font_to_conf(font_desc_str):
    try:
        with open(CONF_PATH, "w", encoding="utf-8") as f:
            f.write(font_desc_str + "\n")
    except Exception:
        pass

class DictWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title=APP_TITLE)
        self.set_default_size(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.en_bg = load_kbg_dat(EN_BG_PATH)
        self.bg_en = load_kbg_dat(BG_EN_PATH)

        self.current_dict = {}
        self.current_results = []

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        main_box.set_border_width(5)
        self.add(main_box)

        top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        main_box.pack_start(top_box, False, False, 0)

        self.entry = Gtk.Entry()
        self.entry.set_width_chars(30)
        self.entry.set_size_request(ENTRY_WIDTH, ENTRY_HEIGHT)
        
        # Свързване на натискания Enter с новата функция
        self.entry.connect("activate", self.on_entry_activate)
        top_box.pack_start(self.entry, False, False, 0)

        self.font_button = Gtk.Button(label="Избор на шрифт")
        self.font_button.connect("clicked", self.on_font_button_clicked)
        top_box.pack_start(self.font_button, True, True, 0)

        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        main_box.pack_start(bottom_box, True, True, 0)

        self.left_scroller = Gtk.ScrolledWindow()
        self.left_scroller.set_size_request(LEFT_WIDTH, LEFT_HEIGHT)
        self.left_scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        bottom_box.pack_start(self.left_scroller, False, False, 0)

        self.word_listbox = Gtk.ListBox()
        self.word_listbox.connect("row-selected", self.on_word_selected)
        self.left_scroller.add(self.word_listbox)

        self.right_scroller = Gtk.ScrolledWindow()
        self.right_scroller.set_size_request(RIGHT_WIDTH, RIGHT_HEIGHT)
        self.right_scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        bottom_box.pack_start(self.right_scroller, True, True, 0)

        self.textview = Gtk.TextView()
        self.textview.set_editable(False)
        self.textview.set_cursor_visible(False)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.right_scroller.add(self.textview)

        font_desc_str = load_font_from_conf()
        if font_desc_str:
            font_desc = Pango.FontDescription(font_desc_str)
            self.apply_font(font_desc)

        self.show_all()

    def apply_font(self, font_desc: Pango.FontDescription):
        self.entry.modify_font(font_desc)
        self.textview.modify_font(font_desc)
        for row in self.word_listbox.get_children():
            child = row.get_child()
            if isinstance(child, Gtk.Label):
                label.modify_font(font_desc)

    def on_font_button_clicked(self, button):
        dialog = Gtk.FontChooserDialog(
            title="Избор на шрифт",
            parent=self,
        )
        dialog.set_modal(True)
        dialog.set_resizable(True)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            font_desc_str = dialog.get_font()
            font_desc = Pango.FontDescription(font_desc_str)
            self.apply_font(font_desc)
            save_font_to_conf(font_desc_str)

        dialog.destroy()

    # Функция, която извършва търсенето при натискане на Enter
    def on_entry_activate(self, entry):
        text = entry.get_text().strip()
        self.update_results(text)

    def update_results(self, query):
        self.word_listbox.foreach(self.word_listbox.remove)  # Clean old results
        self.current_results.clear()

        if not query:
            self.textview.get_buffer().set_text("")
            return

        self.current_dict = self.bg_en if is_cyrillic(query) else self.en_bg

        q_lower = query.lower()
        matches = [word for word in self.current_dict if word.lower().startswith(q_lower)]

        matches.sort()
        self.current_results.extend(matches)

        for w in matches:
            label = Gtk.Label(label=w, xalign=0.0)
            row = Gtk.ListBoxRow()
            row.add(label)
            self.word_listbox.add(row)

        self.word_listbox.show_all()

        if matches:
            self.word_listbox.select_row(self.word_listbox.get_row_at_index(0))
            self.show_translation(matches[0])
        else:
            self.textview.get_buffer().set_text("")

    def on_word_selected(self, listbox, row):
        if row is None:
            return
        label = row.get_child()
        if isinstance(label, Gtk.Label):
            word = label.get_text()
            self.show_translation(word)

    def show_translation(self, word):
        translation = self.current_dict.get(word, "")
        buf = self.textview.get_buffer()
        buf.set_text(translation if translation else "Превод не е намерен.")

def main():
    if not os.path.exists(DICT_DIR):
        os.makedirs(DICT_DIR, exist_ok=True)

    win = DictWindow()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()

if __name__ == "__main__":
    main()
