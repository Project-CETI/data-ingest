from functools import partial
import hashlib
from pathlib import Path
from typing import Any, BinaryIO, Callable, Iterable

from tqdm import tqdm


def create_progress_bar(file_path: Path, file_op_description: str) -> tqdm:
    """Report progress and operation speed"""

    return tqdm(
        desc=f'{file_op_description} {file_path.name}',
        total=file_path.stat().st_size,
        unit='B',
        unit_scale=True,
        position=0,
    )

create_uploader_progress_bar = partial(create_progress_bar, file_op_description="uploading")
create_hashing_progress_bar = partial(create_progress_bar, file_op_description="hashing")


def file_chunks_inter(fd: BinaryIO, chunk_size: int) -> Iterable[bytes]:
    """Create an iterable that reads file by chunks of target size"""

    while True:
        chunk = fd.read(chunk_size)
        if not chunk:
            break

        yield chunk


def sha256sum(file_path: str, callback: Callable[[int], Any] = None) -> str:
    """Get sha256 digest of the local file"""

    h = hashlib.sha256()
    with open(file_path, 'rb') as file:
        for chunk in file_chunks_inter(file, h.block_size):
            h.update(chunk)

            if callback:
                callback(len(chunk))

    return h.hexdigest()
