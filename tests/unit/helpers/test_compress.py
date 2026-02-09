#  This file is part of debcraft.
#
#  Copyright 2026 Canonical Ltd.
#
#  This program is free software: you can redistribute it and/or modify it
#  under the terms of the GNU General Public License version 3, as
#  published by the Free Software Foundation.
#
#  This program is distributed in the hope that it will be useful, but WITHOUT
#  ANY WARRANTY; without even the implied warranties of MERCHANTABILITY,
#  SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR PURPOSE.
#  See the GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Tests for debcraft's compress helper."""

from pathlib import Path

import pytest
from debcraft.helpers import compress


@pytest.mark.parametrize(
    ("link_name", "target_val", "is_absolute"),
    [
        # Absolute link: points to /usr/share/man/man1/ls.1
        pytest.param(
            "usr/bin/ls-link", "/usr/share/man/man1/ls.1", True, id="absolute"
        ),
        # Relative link: README.txt points to README in the same dir
        pytest.param("usr/share/doc/pkg/README.txt", "README", False, id="relative"),
    ],
)
def test_fix_symlinks(tmp_path, link_name, target_val, is_absolute):
    root = tmp_path / "root"
    root.mkdir()

    # 1. Define the actual file that "exists" in our build
    # For absolute test: usr/share/man/man1/ls.1
    # For relative test: usr/share/doc/pkg/README
    if is_absolute:
        real_file_path = root / Path(target_val).relative_to("/")
    else:
        real_file_path = (root / Path(link_name).parent / target_val).resolve()

    real_file_path.parent.mkdir(parents=True, exist_ok=True)
    real_file_path.touch()

    # 2. Create the symlink
    link_path = root / link_name
    link_path.parent.mkdir(parents=True, exist_ok=True)
    link_path.symlink_to(target_val)

    # 3. Create translation map
    translation_map = {real_file_path: real_file_path.with_suffix(".gz")}

    # 4. Run the function
    compress._fix_symlinks([link_path], translation_map, root)

    # 5. Verify the link now points to the .gz version of the target filename
    expected_target = Path(target_val).name + ".gz"
    assert link_path.readlink() == Path(expected_target)


@pytest.mark.parametrize(
    ("path_str", "size", "expected"),
    [
        # Hard Exclusions
        pytest.param("usr/share/doc/copyright", 100, False, id="copyright-exclusion"),
        pytest.param("usr/share/doc/file.jpg", 10000, False, id="jpg-exclusion"),
        pytest.param("usr/share/doc/file.png", 10000, False, id="png-exclusion"),
        pytest.param("usr/share/doc/file.pdf", 10000, False, id="pdf-exclusion"),
        pytest.param("usr/share/doc/file.zip", 10000, False, id="zip-exclusion"),
        pytest.param("usr/share/doc/file.gz", 10000, False, id="gz-exclusion"),
        # Mandatory Compression (man/info)
        pytest.param("usr/share/man/man1/ls.1", 100, True, id="man-page"),
        pytest.param("usr/share/info/dir", 100, True, id="info-file"),
        # Changelogs
        pytest.param("usr/share/doc/pkg/changelog", 100, True, id="changelog"),
        pytest.param(
            "usr/share/doc/pkg/changelog.Debian", 100, True, id="changelog-debian"
        ),
        pytest.param(
            "usr/share/doc/pkg/CHANGELOG.html", 100, True, id="changelog-uppercase"
        ),
        # Documentation size threshold
        pytest.param(
            "usr/share/doc/pkg/README", 4097, True, id="large-readme"
        ),  # > 4kb
        pytest.param("usr/share/doc/pkg/README", 4096, False, id="small-readme"),
        # Random file outside policy
        pytest.param("usr/bin/binary", 10000, False, id="other-file"),
    ],
)
def test_should_compress(tmp_path, path_str, size, expected):
    path = tmp_path / path_str
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("wb") as f:
        f.truncate(size)

    assert compress._should_compress(path, tmp_path) == expected
