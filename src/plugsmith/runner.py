"""Subprocess streaming for dmrconf commands.

SubprocessRunner is a mixin for Textual Widgets/Screens that need to stream
dmrconf output into the UI without blocking the event loop.

Usage:
    class MyPane(Widget, SubprocessRunner):
        def on_subprocess_runner_output_line(self, msg):
            self.output_log.write_line(msg.line, style="yellow" if msg.is_stderr else None)

        def on_subprocess_runner_process_finished(self, msg):
            if msg.returncode == 0:
                self.notify("Done!")
"""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import Optional

from textual.message import Message
from textual.worker import work


class SubprocessRunner:
    """Mixin for any Widget/Screen that needs to stream dmrconf output."""

    # ------------------------------------------------------------------
    # Messages posted to the widget tree
    # ------------------------------------------------------------------

    class OutputLine(Message):
        """A single line of output from the subprocess."""

        def __init__(self, line: str, is_stderr: bool = False) -> None:
            super().__init__()
            self.line = line
            self.is_stderr = is_stderr

    class ProcessStarted(Message):
        """Posted when the subprocess starts."""

        def __init__(self, cmd: list[str]) -> None:
            super().__init__()
            self.cmd = cmd

    class ProcessFinished(Message):
        """Posted when the subprocess exits."""

        def __init__(self, returncode: int, cmd: list[str]) -> None:
            super().__init__()
            self.returncode = returncode
            self.cmd = cmd

    # ------------------------------------------------------------------
    # Worker
    # ------------------------------------------------------------------

    @work(thread=True)
    def run_command(
        self,
        cmd: list[str],
        cwd: Optional[Path] = None,
    ) -> None:
        """Run *cmd* in a background thread, posting messages per line.

        Stdout and stderr are drained concurrently so neither can block.
        """
        self.post_message(SubprocessRunner.ProcessStarted(cmd))  # type: ignore[attr-defined]

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError:
            self.post_message(SubprocessRunner.OutputLine(  # type: ignore[attr-defined]
                f"ERROR: command not found: {cmd[0]}", is_stderr=True
            ))
            self.post_message(SubprocessRunner.ProcessFinished(-1, cmd))  # type: ignore[attr-defined]
            return
        except OSError as e:
            self.post_message(SubprocessRunner.OutputLine(str(e), is_stderr=True))  # type: ignore[attr-defined]
            self.post_message(SubprocessRunner.ProcessFinished(-1, cmd))  # type: ignore[attr-defined]
            return

        def _drain(stream: object, is_stderr: bool) -> None:
            for line in stream:  # type: ignore[union-attr]
                line = line.rstrip("\n")
                self.post_message(SubprocessRunner.OutputLine(line, is_stderr=is_stderr))  # type: ignore[attr-defined]

        t_out = threading.Thread(target=_drain, args=(proc.stdout, False), daemon=True)
        t_err = threading.Thread(target=_drain, args=(proc.stderr, True), daemon=True)
        t_out.start()
        t_err.start()
        t_out.join()
        t_err.join()

        returncode = proc.wait()
        self.post_message(SubprocessRunner.ProcessFinished(returncode, cmd))  # type: ignore[attr-defined]
