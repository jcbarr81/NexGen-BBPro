"""Process-based worker for generating player avatars.

This module provides a helper that runs the expensive avatar generation
in a separate :class:`multiprocessing.Process`. Progress updates and final
status messages are communicated back to the parent process via a
:meth:`multiprocessing.Queue`.
"""

from __future__ import annotations

from multiprocessing import Process, Queue
from typing import Any, Tuple


def _worker(queue: Queue, players: Any, teams: Any) -> None:
    """Run avatar generation and emit progress to *queue*.

    Any exception raised during generation is caught and reported back
    through the queue so the caller can surface the error in the UI.
    """
    from utils.avatar_generator import generate_player_avatars as gen_avatars

    try:
        def cb(done: int, _total: int) -> None:
            queue.put(("progress", done))

        out_dir = gen_avatars(
            progress_callback=cb,
            use_sdxl=True,
            players=players,
            teams=teams,
            controlnet_path=None,
            ip_adapter_path=None,
        )
        queue.put(("finished", out_dir))
    except Exception as exc:  # pragma: no cover - propagated via queue
        queue.put(("error", str(exc)))


def start_avatar_generation(players: Any, teams: Any) -> Tuple[Process, Queue]:
    """Start the avatar generation process.

    Returns the spawned :class:`multiprocessing.Process` and the
    :class:`multiprocessing.Queue` used for communication.
    """
    queue: Queue = Queue()
    process = Process(target=_worker, args=(queue, players, teams), daemon=True)
    process.start()
    return process, queue


__all__ = ["start_avatar_generation"]
