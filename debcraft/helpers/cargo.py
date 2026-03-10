#  This file is part of debcraft.
#
#  Copyright 2025 Canonical Ltd.
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

"""Debcraft Cargo helper service."""

import pathlib
import re
import subprocess
from typing import Any, cast

from debcraft import errors, models

from .helpers import Helper


class Cargo(Helper):
    """Debcraft Cargo helper.

    Verify if rustc and librust-<name>-dev packages are listed as build
    packages, and add matches to the X-Cargo-Built-Using field in the deb
    package control file.

    This is an experimental implementation. Static library and license
    tracking for Built-Using not currently handled.
    """

    def run(
        self,
        *,
        project: models.Project,
        package_name: str,
        prime_dir: pathlib.Path,
        **kwargs: Any,  # noqa: ARG002
    ) -> None:
        """Add metadata related to rust."""
        lockfile = prime_dir / "usr" / "share" / "docs" / package_name / "Cargo.lock.gz"
        if not lockfile.exists():
            return

        package = re.compile(
            r"^(?:rustc(?:-\d+\.\d+)?|librust-[a-z0-9]+(?:-[a-z0-9]+)*-dev)$"
        )

        for name in [p for p in project.build_packages if package.fullmatch(p)]:
            cmd = ["dpkg-query", "-W", "-f=${Version}", name]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                version = result.stdout.strip()
                entry = {f"{name} (= {version})"}
                Helper.control_fields["Built-Using"] = (
                    cast(set[str], Helper.control_fields.get("Built-Using", set()))
                    | entry
                )
                Helper.control_fields["X-Cargo-Built-Using"] = entry
            except subprocess.CalledProcessError:
                raise errors.DebcraftError(f"cannot obtain '{name}' package version")
