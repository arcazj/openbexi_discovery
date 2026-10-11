"""Sign Windows releases using a certificate store or Microsoft Artifact Signing."""

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urlsplit


def signtool_path():
    configured = os.getenv("OPENBEXI_SIGNTOOL")
    if configured:
        if not Path(configured).is_file():
            raise RuntimeError("OPENBEXI_SIGNTOOL must point to Windows SDK signtool.exe.")
        return str(Path(configured).resolve())
    found = shutil.which("signtool")
    if found:
        return found
    sdk = Path(os.getenv("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Windows Kits/10/bin"
    candidates = sorted(sdk.glob("*/x64/signtool.exe"), reverse=True)
    if candidates:
        return str(candidates[0])
    raise RuntimeError("Install Windows SDK SignTool or set OPENBEXI_SIGNTOOL before signing.")


def run_signtool(arguments):
    try:
        result = subprocess.run(arguments, capture_output=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("SignTool could not complete. Check the signing tools and account access.") from None
    # SignTool also returns 2 for warnings, including a missing timestamp.
    if result.returncode:
        raise RuntimeError("SignTool failed or reported a warning. Check the certificate, timestamp service, and signing account. Do not publish this artifact.")


def verify_signature(path, tool=None):
    run_signtool([tool or signtool_path(), "verify", "/pa", "/all", "/tw", str(path)])


@dataclass
class WindowsSigner:
    tool: str
    identity_arguments: list
    timestamp_url: str

    @classmethod
    def from_environment(cls, required=False):
        thumbprint = os.getenv("OPENBEXI_SIGN_CERT_SHA1", "").strip()
        dlib = os.getenv("OPENBEXI_SIGN_DLIB", "").strip()
        metadata = os.getenv("OPENBEXI_SIGN_METADATA", "").strip()
        if not any((thumbprint, dlib, metadata)):
            if required:
                raise RuntimeError("A verified publisher signing identity is required. Configure a certificate or Microsoft Artifact Signing.")
            return None
        if thumbprint:
            if dlib or metadata or not re.fullmatch(r"[a-fA-F0-9]{40}", thumbprint):
                raise ValueError("Set a 40-digit certificate thumbprint OR the Artifact Signing paths, not both.")
            identity = ["/s", "My", "/sha1", thumbprint]
        else:
            if not dlib or not metadata or not Path(dlib).is_file() or not Path(metadata).is_file():
                raise ValueError("Artifact Signing requires both OPENBEXI_SIGN_DLIB and OPENBEXI_SIGN_METADATA files.")
            identity = ["/dlib", str(Path(dlib).resolve()), "/dmdf", str(Path(metadata).resolve())]
        timestamp = os.getenv("OPENBEXI_SIGN_TIMESTAMP_URL", "http://timestamp.acs.microsoft.com").strip()
        url = urlsplit(timestamp)
        if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
            raise ValueError("Use an HTTP(S) RFC 3161 timestamp service URL without credentials.")
        return cls(signtool_path(), identity, timestamp)

    def sign(self, path):
        path = Path(path).resolve(strict=True)
        if not path.is_file():
            raise ValueError("Signing requires a file.")
        run_signtool([self.tool, "sign", "/fd", "SHA256", "/tr", self.timestamp_url, "/td", "SHA256",
                      "/d", "OpenBEXI Discovery", *self.identity_arguments, str(path)])
        verify_signature(path, self.tool)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    options = parser.parse_args()
    WindowsSigner.from_environment(required=True).sign(options.file)
