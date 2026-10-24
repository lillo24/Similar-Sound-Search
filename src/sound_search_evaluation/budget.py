"""Fresh complete managed-tree inventory using cached Windows directory-entry metadata."""

import os
from pathlib import Path

from similar_sound_search.resources import MANAGED
from similar_sound_search.resources import CatalogueBudget as BaseBudget
from similar_sound_search.storage import ResourceError, contained, is_link


class CatalogueBudget(BaseBudget):
    """Same roots/caps/file-count guard; avoid two extra path stats per historic file.

    Every bounded process still scans the entire actual managed tree. This is not
    a historical-size snapshot or a permission-error fallback. Scandir carries
    native file sizes on Windows; directory junctions and symlinks stay excluded.
    """

    def managed_bytes(self):
        if self._managed is not None:
            return self._managed
        size = count = 0
        for relative in MANAGED:
            base = contained(self.root / relative, self.root)
            if not base.exists() or is_link(base):
                continue
            pending = [base]
            while pending:
                directory = pending.pop()
                self.check_time("disk inventory", directory)
                with os.scandir(directory) as entries:
                    for entry in entries:
                        if entry.is_dir(follow_symlinks=False):
                            if not entry.is_symlink() and not os.path.isjunction(entry.path):
                                pending.append(Path(entry.path))
                            continue
                        count += 1
                        if not entry.is_symlink():
                            size += entry.stat(follow_symlinks=False).st_size
                        if count > 100000:
                            raise ResourceError("D02 disk inventory exceeds 100000 managed files")
                        if count % 256 == 0:
                            self.check_time("disk inventory", directory)
        self._managed = size
        return size
