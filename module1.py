import tkinter as tk
from tkinter import ttk, messagebox
import difflib
import re

# Simple Tkinter app to compare a reference string against one or more candidate strings.
# - Enter one reference string.
# - Enter one candidate per line (multiple lines allowed).
# - Choose mode: Character or Word tokens.
# - Optional: ignore case, collapse whitespace.
# - Press Compare to see per-line summary and detailed side-by-side diffs with highlighting.

TOKEN_WORD_RE = re.compile(r'\w+|[^\w\s]|\s+', re.UNICODE)


def tokenize_chars(s: str):
    return list(s)


def tokenize_words(s: str):
    return TOKEN_WORD_RE.findall(s)


def normalize_text(s: str, ignore_case: bool, collapse_ws: bool):
    if ignore_case:
        s = s.lower()
    if collapse_ws:
        s = re.sub(r'\s+', ' ', s).strip()
    return s


class StrComparatorApp:
    def __init__(self, root):
        self.root = root
        root.title("String Comparator")
        self._build_ui()
        self.diffs_cache = []  # store (ref_tokens, cand_tokens, diff_list) for selected candidate index

    def _build_ui(self):
        frm = ttk.Frame(self.root, padding=8)
        frm.grid(sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        top = ttk.Frame(frm)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Reference string:").grid(row=0, column=0, sticky="w")
        self.ref_entry = tk.Text(top, height=2, wrap="word")
        self.ref_entry.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(2, 8))

        left = ttk.Frame(frm)
        left.grid(row=1, column=0, sticky="nsew")
        frm.rowconfigure(1, weight=1)
        frm.columnconfigure(0, weight=1)

        ttk.Label(left, text="Candidates (one per line):").grid(row=0, column=0, sticky="w")
        self.cand_text = tk.Text(left, height=10, wrap="none")
        self.cand_text.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        options = ttk.Frame(left)
        options.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        self.mode = tk.StringVar(value="char")
        ttk.Radiobutton(options, text="Character", variable=self.mode, value="char").grid(row=0, column=0)
        ttk.Radiobutton(options, text="Word", variable=self.mode, value="word").grid(row=0, column=1)
        self.ignore_case = tk.BooleanVar(value=False)
        ttk.Checkbutton(options, text="Ignore case", variable=self.ignore_case).grid(row=0, column=2, padx=(10, 0))
        self.collapse_ws = tk.BooleanVar(value=False)
        ttk.Checkbutton(options, text="Collapse whitespace", variable=self.collapse_ws).grid(row=0, column=3, padx=(10, 0))

        btns = ttk.Frame(left)
        btns.grid(row=3, column=0, sticky="ew", pady=(6, 0))
        ttk.Button(btns, text="Compare", command=self.on_compare).grid(row=0, column=0)
        ttk.Button(btns, text="Clear", command=self.on_clear).grid(row=0, column=1, padx=(6, 0))

        right = ttk.Frame(frm)
        right.grid(row=1, column=1, sticky="nsew")
        frm.columnconfigure(1, weight=1)
        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)

        ttk.Label(right, text="Summary:").grid(row=0, column=0, sticky="w")
        self.summary_list = tk.Listbox(right, height=6)
        self.summary_list.grid(row=1, column=0, sticky="ew")
        self.summary_list.bind("<<ListboxSelect>>", self.on_select_summary)

        detail_lbl = ttk.Label(right, text="Detailed diff (left = reference, right = candidate):")
        detail_lbl.grid(row=2, column=0, sticky="w", pady=(6, 0))
        detail_pane = ttk.Frame(right)
        detail_pane.grid(row=3, column=0, sticky="nsew")
        detail_pane.rowconfigure(0, weight=1)
        detail_pane.columnconfigure(0, weight=1)
        detail_pane.columnconfigure(1, weight=1)

        self.ref_text = tk.Text(detail_pane, wrap="none", height=12)
        self.ref_text.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self.cand_text_detail = tk.Text(detail_pane, wrap="none", height=12)
        self.cand_text_detail.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        # Tag styles
        for t, cfg in [
            ("match", {"background": "#e8ffe8"}),
            ("delete", {"background": "#ffe8e8"}),
            ("insert", {"background": "#e8f0ff"}),
            ("diff", {"background": "#fff3bf"}),
        ]:
            self.ref_text.tag_configure(t, **cfg)
            self.cand_text_detail.tag_configure(t, **cfg)

        # Add simple instructions
        inst = ttk.Label(right, text="Tip: place reference text exactly as intended. Candidates can be pasted one-per-line.")
        inst.grid(row=4, column=0, sticky="w", pady=(6, 0))

    def on_clear(self):
        self.ref_entry.delete("1.0", "end")
        self.cand_text.delete("1.0", "end")
        self.summary_list.delete(0, "end")
        self.ref_text.delete("1.0", "end")
        self.cand_text_detail.delete("1.0", "end")
        self.diffs_cache.clear()

    def on_compare(self):
        ref_raw = self.ref_entry.get("1.0", "end").rstrip("\n")
        if not ref_raw.strip():
            messagebox.showinfo("No reference", "Please enter a reference string to compare against.")
            return
        cand_raw = self.cand_text.get("1.0", "end").rstrip("\n")
        candidates = [line for line in cand_raw.splitlines() if line != ""]
        if not candidates:
            messagebox.showinfo("No candidates", "Please enter one or more candidate strings (one per line).")
            return

        mode = self.mode.get()
        ignore_case = self.ignore_case.get()
        collapse_ws = self.collapse_ws.get()

        ref_proc = normalize_text(ref_raw, ignore_case, collapse_ws)
        self.diffs_cache.clear()
        self.summary_list.delete(0, "end")
        for idx, cand in enumerate(candidates):
            cand_proc = normalize_text(cand, ignore_case, collapse_ws)
            if mode == "char":
                rtokens = tokenize_chars(ref_proc)
                ctokens = tokenize_chars(cand_proc)
            else:
                rtokens = tokenize_words(ref_proc)
                ctokens = tokenize_words(cand_proc)

            diff = list(difflib.ndiff(rtokens, ctokens))
            # Determine if exact (all initial tokens same and lengths same)
            is_exact = all(line.startswith(" ") for line in diff) and sum(1 for _ in diff) > 0 and len(rtokens) == len(ctokens)
            if is_exact:
                summary = f"#{idx+1}: Exact"
            else:
                # Provide short summary: counts of insert/delete/replace
                inserts = sum(1 for line in diff if line.startswith("+ "))
                deletes = sum(1 for line in diff if line.startswith("- "))
                replaces = min(inserts, deletes)
                changes = inserts + deletes
                summary = f"#{idx+1}: Differences — inserts:{inserts} deletes:{deletes} total changes:{changes}"
            self.summary_list.insert("end", summary)
            self.diffs_cache.append((rtokens, ctokens, diff, candidates[idx], ref_raw))
        # auto-select first item
        if self.diffs_cache:
            self.summary_list.selection_clear(0, "end")
            self.summary_list.selection_set(0)
            self.show_detail(0)

    def on_select_summary(self, event):
        sel = self.summary_list.curselection()
        if not sel:
            return
        idx = sel[0]
        self.show_detail(idx)

    def show_detail(self, idx: int):
        rtokens, ctokens, diff, cand_original, ref_original = self.diffs_cache[idx]
        # Clear widgets
        self.ref_text.config(state="normal")
        self.cand_text_detail.config(state="normal")
        self.ref_text.delete("1.0", "end")
        self.cand_text_detail.delete("1.0", "end")

        # Build side-by-side strings and apply tags
        ref_pos = 0
        cand_pos = 0

        for line in diff:
            code = line[:2]
            token = line[2:]
            if code == "  ":
                # match: put in both
                start_r = f"1.0+{ref_pos}c"
                start_c = f"1.0+{cand_pos}c"
                self.ref_text.insert("end", token)
                self.cand_text_detail.insert("end", token)
                end_r = f"1.0+{ref_pos + len(token)}c"
                end_c = f"1.0+{cand_pos + len(token)}c"
                # mark matches lightly
                self.ref_text.tag_add("match", start_r, end_r)
                self.cand_text_detail.tag_add("match", start_c, end_c)
                ref_pos += len(token)
                cand_pos += len(token)
            elif code == "- ":
                # token only in ref
                start_r = f"1.0+{ref_pos}c"
                self.ref_text.insert("end", token)
                end_r = f"1.0+{ref_pos + len(token)}c"
                self.ref_text.tag_add("delete", start_r, end_r)
                # Insert placeholder in candidate view to keep visual alignment (optional)
                # We'll insert the same length of spaces so that side-by-side roughly lines up
                placeholder = ""  # keep empty to prevent huge spaces; user can see deletion in ref
                if placeholder:
                    start_c = f"1.0+{cand_pos}c"
                    self.cand_text_detail.insert("end", placeholder)
                    end_c = f"1.0+{cand_pos + len(placeholder)}c"
                    self.cand_text_detail.tag_add("diff", start_c, end_c)
                    cand_pos += len(placeholder)
                ref_pos += len(token)
            elif code == "+ ":
                # token only in candidate
                start_c = f"1.0+{cand_pos}c"
                self.cand_text_detail.insert("end", token)
                end_c = f"1.0+{cand_pos + len(token)}c"
                self.cand_text_detail.tag_add("insert", start_c, end_c)
                # candidate-only tokens are not inserted into ref view
                cand_pos += len(token)

        # Put original full strings as top comments for clarity (not highlighted)
        # Prepend original strings at the top of each box for user context
        # We'll clear and reinsert with originals separated
        self.ref_text.insert("1.0", ref_original + "\n\n")
        self.cand_text_detail.insert("1.0", cand_original + "\n\n")

        # Optionally, add simple pointer lines showing indexes of differences (not implemented)
        self.ref_text.config(state="disabled")
        self.cand_text_detail.config(state="disabled")

        # Focus to detail pane
        self.ref_text.see("1.0")
        self.cand_text_detail.see("1.0")


def main():
    root = tk.Tk()
    app = StrComparatorApp(root)
    root.geometry("1000x600")
    root.mainloop()


if __name__ == "__main__":
    main()
