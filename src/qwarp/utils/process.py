"""Trusted, bounded Linux subprocess execution; no Qt or raw diagnostic logging."""

import os
import selectors
import shutil
import signal
import stat
import subprocess
import threading
import time
from pathlib import Path

OUTPUT_LIMIT = 1024 * 1024


class CommandError(RuntimeError):
    """A safe-to-display execution failure with no command or output payload."""


def resolve_executable(name: str, *, privileged: bool = False) -> str:
    candidate = shutil.which(name, path="/usr/bin:/bin" if privileged else None)
    if not candidate:
        raise FileNotFoundError("Required executable not installed")
    original = Path(os.path.abspath(candidate))
    resolved = original.resolve(strict=True)
    allowed_owners = {0} if privileged else {0, os.getuid()}
    # Validate both the PATH entry and every resolved ancestor of symlink paths.
    paths = {resolved}
    for path in (original, *original.parents):
        target = path.resolve(strict=True)
        paths.update((target, *target.parents))
    for path in paths:
        info = path.stat()
        if info.st_uid not in allowed_owners or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise CommandError("Unsafe executable permissions")
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise CommandError("Executable is not runnable")
    if privileged and resolved.parent not in {Path("/usr/bin"), Path("/bin")}:
        raise CommandError("Privileged executable is outside system locations")
    return str(resolved)


def _terminate(process: subprocess.Popen) -> None:
    # Every child has a dedicated session: descendants cannot keep pipes open.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def run_command(
    command: list[str],
    *,
    timeout: float,
    cancel_event: threading.Event | None = None,
    privileged: bool = False,
    **_options,
) -> subprocess.CompletedProcess[str]:
    """Capture at most 1 MiB per stream, with deadline and cancellation cleanup."""
    if cancel_event is not None and cancel_event.is_set():
        raise CommandError("Command cancelled")
    executable = resolve_executable(command[0], privileged=privileged)
    deadline = time.monotonic() + timeout
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    with subprocess.Popen(
        [executable, *command[1:]],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    ) as child:
        try:
            with selectors.DefaultSelector() as selector:
                for label in buffers:
                    pipe = getattr(child, label)
                    os.set_blocking(pipe.fileno(), False)
                    selector.register(pipe, selectors.EVENT_READ, label)
                while selector.get_map() or child.poll() is None:
                    if cancel_event is not None and cancel_event.is_set():
                        raise CommandError("Command cancelled")
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise CommandError("Command timeout")
                    for key, _events in selector.select(min(remaining, 0.05)):
                        try:
                            chunk = os.read(key.fd, 65536)
                        except BlockingIOError:
                            continue
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        buffer = buffers[key.data]
                        if len(buffer) + len(chunk) > OUTPUT_LIMIT:
                            raise CommandError("Command output limit exceeded")
                        buffer.extend(chunk)
                child.wait()
        except BaseException:
            _terminate(child)
            raise
    return subprocess.CompletedProcess(
        command,
        child.returncode,
        buffers["stdout"].decode("utf-8", errors="replace"),
        buffers["stderr"].decode("utf-8", errors="replace"),
    )
