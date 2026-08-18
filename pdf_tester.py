"""
pdf_tester.py

Core logic for testing candidate passwords against a password-protected PDF
that the user owns or is explicitly authorized to access.

This module intentionally does ONLY the following:
    - Validates that a selected file is a real, readable, encrypted PDF.
    - Generates candidate passwords lazily according to a fixed, narrow
      pattern (4 uppercase letters + 4 digit year in a bounded range).
    - Tests each candidate using pypdf's normal, public decrypt() API.
    - Reports progress back to the caller via a callback.
    - Supports clean cancellation.

It does NOT attempt to bypass, weaken, or exploit PDF encryption in any
way. All password checks go through pypdf's standard decryption routine,
which is the same mechanism a PDF viewer would use when a user types a
password into a prompt.

This class has no knowledge of Tkinter and does not touch any GUI
widgets directly, so it can be safely driven from a background thread.
"""

from __future__ import annotations

import os
import string
import threading
import time
from dataclasses import dataclass
from typing import Callable, Iterator, Optional

from pypdf import PdfReader
from pypdf.errors import PdfReadError, FileNotDecryptedError


# --------------------------------------------------------------------------
# Constants describing the candidate password pattern
# --------------------------------------------------------------------------

UPPERCASE_LETTERS = string.ascii_uppercase  # "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
PREFIX_LENGTH = 4
YEAR_START = 1990
YEAR_END = 2007  # inclusive

NUM_PREFIXES = len(UPPERCASE_LETTERS) ** PREFIX_LENGTH  # 26**4 = 456,976
NUM_YEARS = YEAR_END - YEAR_START + 1  # 18
TOTAL_CANDIDATES = NUM_PREFIXES * NUM_YEARS  # 8,225,568


class PDFValidationError(Exception):
    """Raised when the selected file cannot be used for a password search."""


@dataclass
class ProgressUpdate:
    """A snapshot of search progress, sent periodically to the GUI layer."""
    tested: int
    total: int
    current_candidate: str
    elapsed_seconds: float
    rate_per_second: float


@dataclass
class SearchResult:
    """Final outcome of a password search."""
    found: bool
    password: Optional[str]
    tested: int
    elapsed_seconds: float
    stopped_by_user: bool = False


def format_total_candidates() -> str:
    """Return a human-readable description of the total candidate count."""
    return f"{NUM_PREFIXES:,} x {NUM_YEARS} = {TOTAL_CANDIDATES:,}"


def _generate_prefixes() -> Iterator[str]:
    """
    Lazily yield every 4-letter uppercase combination, AAAA..ZZZZ,
    without ever materializing the full list in memory.
    """
    letters = UPPERCASE_LETTERS
    for a in letters:
        for b in letters:
            for c in letters:
                for d in letters:
                    yield a + b + c + d


def generate_candidates() -> Iterator[str]:
    """
    Lazily yield candidate passwords in the form XXXXYYYY, where XXXX is
    an uppercase 4-letter combination and YYYY is a year in
    [YEAR_START, YEAR_END].
    """
    years = [str(y) for y in range(YEAR_START, YEAR_END + 1)]
    for prefix in _generate_prefixes():
        for year in years:
            yield prefix + year


class PDFPasswordTester:
    """
    Validates a PDF and runs a cancellable, progress-reporting brute-force
    search over the fixed candidate pattern described above.

    Usage:
        tester = PDFPasswordTester(path)
        tester.validate()  # raises PDFValidationError on problems
        result = tester.run(
            progress_callback=my_progress_fn,
            progress_interval=0.25,
        )
    """

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> None:
        """
        Verify the file exists, is a readable PDF, and is encrypted.
        Raises PDFValidationError with a user-friendly message otherwise.
        """
        if not self.pdf_path:
            raise PDFValidationError("No PDF selected.")

        if not os.path.isfile(self.pdf_path):
            raise PDFValidationError("The selected file does not exist.")

        if not self.pdf_path.lower().endswith(".pdf"):
            raise PDFValidationError("The selected file is not a .pdf file.")

        try:
            reader = PdfReader(self.pdf_path)
        except PdfReadError:
            raise PDFValidationError(
                "The file could not be read as a valid PDF. "
                "It may be corrupted or malformed."
            )
        except FileNotFoundError:
            raise PDFValidationError("The selected file does not exist.")
        except Exception:
            raise PDFValidationError(
                "The file could not be opened. It may be corrupted, "
                "malformed, or not a valid PDF."
            )

        try:
            is_encrypted = reader.is_encrypted
        except Exception:
            raise PDFValidationError(
                "Could not determine the encryption status of this PDF."
            )

        if not is_encrypted:
            raise PDFValidationError(
                "This PDF is not password-protected. There is no password "
                "to search for."
            )

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Signal the running search to stop as soon as possible."""
        self._stop_event.set()

    def reset(self) -> None:
        """Clear any previous stop signal so the tester can run again."""
        self._stop_event.clear()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def run(
        self,
        progress_callback: Optional[Callable[[ProgressUpdate], None]] = None,
        progress_interval: float = 0.25,
    ) -> SearchResult:
        """
        Run the brute-force search using pypdf's standard decrypt() API.

        progress_callback is invoked periodically (at most every
        progress_interval seconds, or every N attempts) with a
        ProgressUpdate. It is called from whatever thread run() executes
        on -- callers running this in a worker thread are responsible for
        marshalling that data back to their GUI thread safely (e.g. via a
        queue).
        """
        self.reset()
        start_time = time.monotonic()
        tested = 0
        last_report_time = start_time
        # Report at least every N attempts too, in case decryption calls
        # are extremely fast and time-based throttling alone would still
        # allow a huge burst of skipped UI updates.
        report_every_n = 200

        try:
            reader = PdfReader(self.pdf_path)
        except Exception:
            return SearchResult(
                found=False,
                password=None,
                tested=0,
                elapsed_seconds=0.0,
                stopped_by_user=False,
            )

        for candidate in generate_candidates():
            if self._stop_event.is_set():
                elapsed = time.monotonic() - start_time
                return SearchResult(
                    found=False,
                    password=None,
                    tested=tested,
                    elapsed_seconds=elapsed,
                    stopped_by_user=True,
                )

            try:
                # pypdf's public decrypt() is the normal, supported way to
                # check a candidate password against an encrypted PDF. It
                # returns a truthy PasswordType on success (0/False on
                # failure). This does not touch or exploit the underlying
                # encryption implementation.
                match_result = reader.decrypt(candidate)
            except Exception:
                # Malformed/unusual encryption dictionaries can occasionally
                # raise on a given attempt; treat as "wrong password" and
                # keep going rather than crashing the search.
                match_result = 0

            tested += 1

            if match_result:
                elapsed = time.monotonic() - start_time
                return SearchResult(
                    found=True,
                    password=candidate,
                    tested=tested,
                    elapsed_seconds=elapsed,
                    stopped_by_user=False,
                )

            now = time.monotonic()
            should_report = (
                progress_callback is not None
                and (
                    (now - last_report_time) >= progress_interval
                    or tested % report_every_n == 0
                )
            )
            if should_report:
                elapsed = now - start_time
                rate = tested / elapsed if elapsed > 0 else 0.0
                progress_callback(
                    ProgressUpdate(
                        tested=tested,
                        total=TOTAL_CANDIDATES,
                        current_candidate=candidate,
                        elapsed_seconds=elapsed,
                        rate_per_second=rate,
                    )
                )
                last_report_time = now

        elapsed = time.monotonic() - start_time
        return SearchResult(
            found=False,
            password=None,
            tested=tested,
            elapsed_seconds=elapsed,
            stopped_by_user=False,
        )
