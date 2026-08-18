"""
main.py

Tkinter GUI for testing candidate passwords against a password-protected
PDF that the user owns or is explicitly authorized to access.

The password search itself runs on a background thread (see
pdf_tester.PDFPasswordTester). This file is only responsible for:
    - Building the GUI.
    - Starting/stopping the worker thread.
    - Safely receiving progress/results from the worker via a thread-safe
      queue and displaying them using Tkinter's after() polling loop.

No Tkinter widgets are ever touched from the worker thread.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from pdf_tester import (
    PDFPasswordTester,
    PDFValidationError,
    ProgressUpdate,
    SearchResult,
    TOTAL_CANDIDATES,
    YEAR_START,
    YEAR_END,
    format_total_candidates,
)


APP_TITLE = "PDF Password Tester"
MIN_WIDTH = 620
MIN_HEIGHT = 460

# Messages placed on the queue by the worker thread. Each is a tuple of
# (kind, payload) so the GUI thread can dispatch on kind.
MSG_PROGRESS = "progress"
MSG_RESULT = "result"
MSG_ERROR = "error"


class PDFPasswordTesterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.root.geometry(f"{MIN_WIDTH}x{MIN_HEIGHT}")

        self.pdf_path_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Select a PDF file to begin.")
        self.current_candidate_var = tk.StringVar(value="-")
        self.tested_var = tk.StringVar(value="0")
        self.elapsed_var = tk.StringVar(value="0.0s")
        self.rate_var = tk.StringVar(value="0 passwords/sec")
        self.progress_pct_var = tk.StringVar(value="0.0%")

        self.tester: PDFPasswordTester | None = None
        self.worker_thread: threading.Thread | None = None
        self.msg_queue: "queue.Queue" = queue.Queue()
        self.search_running = False
        self._poll_job = None

        self._build_style()
        self._build_widgets()
        self._update_button_states()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_style(self):
        style = ttk.Style()
        # "clam" renders consistently and cleanly on Windows.
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        default_font = ("Segoe UI", 10)
        bold_font = ("Segoe UI", 10, "bold")
        heading_font = ("Segoe UI", 11, "bold")
        mono_font = ("Consolas", 10)

        style.configure("TLabel", font=default_font)
        style.configure("TButton", font=default_font, padding=6)
        style.configure("TLabelframe.Label", font=heading_font)
        style.configure("Bold.TLabel", font=bold_font)
        style.configure("Mono.TLabel", font=mono_font)
        style.configure(
            "Result.TLabel", font=("Segoe UI", 12, "bold")
        )

        self.default_font = default_font
        self.mono_font = mono_font

    def _build_widgets(self):
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)

        # -------------------- 1. PDF Selection --------------------
        file_frame = ttk.LabelFrame(outer, text="PDF File", padding=10)
        file_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        file_frame.columnconfigure(0, weight=1)

        self.path_entry = ttk.Entry(
            file_frame, textvariable=self.pdf_path_var, state="readonly"
        )
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.browse_btn = ttk.Button(
            file_frame, text="Browse...", command=self._on_browse
        )
        self.browse_btn.grid(row=0, column=1)

        # -------------------- 2. Search Settings --------------------
        settings_frame = ttk.LabelFrame(outer, text="Search Settings", padding=10)
        settings_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        settings_frame.columnconfigure(0, weight=1)

        ttk.Label(
            settings_frame, text="Password format: XXXXYYYY"
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            settings_frame,
            text="X = uppercase letter (A-Z)    YYYY = year",
        ).grid(row=1, column=0, sticky="w")
        ttk.Label(
            settings_frame, text=f"Years: {YEAR_START} - {YEAR_END}"
        ).grid(row=2, column=0, sticky="w", pady=(4, 0))
        ttk.Label(
            settings_frame,
            text=f"Total candidate passwords: {format_total_candidates()}",
            style="Bold.TLabel",
        ).grid(row=3, column=0, sticky="w", pady=(4, 0))

        # -------------------- 3. Controls --------------------
        controls_frame = ttk.Frame(outer)
        controls_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        self.start_btn = ttk.Button(
            controls_frame, text="Start", command=self._on_start
        )
        self.start_btn.pack(side="left")

        self.stop_btn = ttk.Button(
            controls_frame, text="Stop", command=self._on_stop
        )
        self.stop_btn.pack(side="left", padx=(8, 0))

        # -------------------- 4. Progress --------------------
        progress_frame = ttk.LabelFrame(outer, text="Progress", padding=10)
        progress_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        progress_frame.columnconfigure(1, weight=1)

        self.progress_bar = ttk.Progressbar(
            progress_frame, orient="horizontal", mode="determinate", maximum=100
        )
        self.progress_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        self._add_stat_row(progress_frame, 1, "Current candidate:", self.current_candidate_var, mono=True)
        self._add_stat_row(progress_frame, 2, "Candidates tested:", self.tested_var)
        self._add_stat_row(progress_frame, 3, "Elapsed time:", self.elapsed_var)
        self._add_stat_row(progress_frame, 4, "Rate:", self.rate_var)
        self._add_stat_row(progress_frame, 5, "Progress:", self.progress_pct_var)

        # -------------------- 5/6. Result / Status --------------------
        result_frame = ttk.LabelFrame(outer, text="Status", padding=10)
        result_frame.grid(row=4, column=0, sticky="nsew")
        outer.rowconfigure(4, weight=1)
        result_frame.columnconfigure(0, weight=1)

        self.status_label = ttk.Label(
            result_frame,
            textvariable=self.status_var,
            style="Result.TLabel",
            wraplength=560,
            justify="left",
        )
        self.status_label.grid(row=0, column=0, sticky="w")

    def _add_stat_row(self, parent, row, label_text, var, mono=False):
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", pady=2)
        style = "Mono.TLabel" if mono else "TLabel"
        ttk.Label(parent, textvariable=var, style=style).grid(
            row=row, column=1, sticky="w", padx=(8, 0), pady=2
        )

    # ------------------------------------------------------------------
    # Button state management
    # ------------------------------------------------------------------

    def _update_button_states(self):
        if self.search_running:
            self.start_btn.state(["disabled"])
            self.stop_btn.state(["!disabled"])
            self.browse_btn.state(["disabled"])
        else:
            self.start_btn.state(["!disabled"])
            self.stop_btn.state(["disabled"])
            self.browse_btn.state(["!disabled"])

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_browse(self):
        path = filedialog.askopenfilename(
            title="Select a password-protected PDF",
            filetypes=[("PDF files", "*.pdf")],
        )
        if path:
            self.pdf_path_var.set(path)
            self.status_var.set("Ready. Press Start to begin searching.")
            self._reset_progress_display()

    def _on_start(self):
        if self.search_running:
            return

        pdf_path = self.pdf_path_var.get().strip()

        tester = PDFPasswordTester(pdf_path)
        try:
            tester.validate()
        except PDFValidationError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return
        except Exception as exc:
            messagebox.showerror(
                APP_TITLE, f"An unexpected error occurred: {exc}"
            )
            return

        self.tester = tester
        self._reset_progress_display()
        self.status_var.set("Searching for password...")
        self.search_running = True
        self._update_button_states()

        # Drain any stale messages from a previous run.
        while not self.msg_queue.empty():
            try:
                self.msg_queue.get_nowait()
            except queue.Empty:
                break

        self.worker_thread = threading.Thread(
            target=self._worker_main, daemon=True
        )
        self.worker_thread.start()

        self._schedule_poll()

    def _on_stop(self):
        if self.tester is not None and self.search_running:
            self.status_var.set("Stopping...")
            self.tester.stop()

    def _on_close(self):
        # Allow the app to close cleanly even if a search is running.
        if self.tester is not None:
            self.tester.stop()
        if self._poll_job is not None:
            try:
                self.root.after_cancel(self._poll_job)
            except Exception:
                pass
        self.root.destroy()

    # ------------------------------------------------------------------
    # Worker thread (NO Tkinter calls allowed in this method or below)
    # ------------------------------------------------------------------

    def _worker_main(self):
        assert self.tester is not None
        try:
            result = self.tester.run(
                progress_callback=self._on_worker_progress,
                progress_interval=0.2,
            )
            self.msg_queue.put((MSG_RESULT, result))
        except Exception as exc:
            self.msg_queue.put((MSG_ERROR, str(exc)))

    def _on_worker_progress(self, update: ProgressUpdate):
        # Called from the worker thread. Only puts data on a thread-safe
        # queue -- never touches Tkinter widgets directly.
        self.msg_queue.put((MSG_PROGRESS, update))

    # ------------------------------------------------------------------
    # GUI-thread polling loop
    # ------------------------------------------------------------------

    def _schedule_poll(self):
        self._poll_job = self.root.after(100, self._poll_queue)

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == MSG_PROGRESS:
                    self._apply_progress(payload)
                elif kind == MSG_RESULT:
                    self._apply_result(payload)
                elif kind == MSG_ERROR:
                    self._apply_error(payload)
        except queue.Empty:
            pass

        if self.search_running:
            self._schedule_poll()

    # ------------------------------------------------------------------
    # Applying updates to widgets (GUI thread only)
    # ------------------------------------------------------------------

    def _reset_progress_display(self):
        self.current_candidate_var.set("-")
        self.tested_var.set("0")
        self.elapsed_var.set("0.0s")
        self.rate_var.set("0 passwords/sec")
        self.progress_pct_var.set("0.0%")
        self.progress_bar["value"] = 0

    def _apply_progress(self, update: ProgressUpdate):
        self.current_candidate_var.set(update.current_candidate)
        self.tested_var.set(f"{update.tested:,}")
        self.elapsed_var.set(f"{update.elapsed_seconds:.1f}s")
        self.rate_var.set(f"{update.rate_per_second:,.0f} passwords/sec")

        if update.total:
            pct = min(100.0, (update.tested / update.total) * 100.0)
        else:
            pct = 0.0
        self.progress_pct_var.set(f"{pct:.4f}%")
        self.progress_bar["value"] = pct

    def _apply_result(self, result: SearchResult):
        self.search_running = False
        self._update_button_states()

        self.tested_var.set(f"{result.tested:,}")
        self.elapsed_var.set(f"{result.elapsed_seconds:.1f}s")
        if result.elapsed_seconds > 0:
            rate = result.tested / result.elapsed_seconds
            self.rate_var.set(f"{rate:,.0f} passwords/sec")

        if result.found:
            self.status_var.set(f"Password Found: {result.password}")
            self.progress_bar["value"] = 100.0
            self.progress_pct_var.set("100.0%")
            messagebox.showinfo(
                APP_TITLE,
                f"Password Found: {result.password}\n\n"
                f"Attempts: {result.tested:,}\n"
                f"Elapsed time: {result.elapsed_seconds:.1f}s",
            )
        elif result.stopped_by_user:
            self.status_var.set(
                f"Search stopped by user. "
                f"Candidates tested: {result.tested:,}."
            )
        else:
            self.status_var.set(
                "Password not found in the specified pattern/range."
            )

    def _apply_error(self, message: str):
        self.search_running = False
        self._update_button_states()
        self.status_var.set("An error occurred during the search.")
        messagebox.showerror(APP_TITLE, f"Search could not be completed:\n{message}")


def main():
    root = tk.Tk()
    app = PDFPasswordTesterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
