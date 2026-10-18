# Third-Party Notices

This inventory records the Python runtime dependencies installed for the first version. Original license texts and notices are preserved in `licenses/`; retain the applicable notices when distributing dependencies. The source project license remains pending owner selection.

OpenAI's hosted API and public data providers have separate service and data-reuse terms. See [commercial licensing notes](COMMERCIAL_LICENSING.md). Three.js is deferred and is not bundled in this release.

| Component | Verified version | Declared license | Preserved notices |
|---|---|---|---|
| annotated-doc | 0.0.5 | MIT | [LICENSE](licenses/annotated-doc-license.txt) |
| annotated-types | 0.7.0 | See license text | [LICENSE](licenses/annotated-types-license.txt) |
| anyio | 4.12.1 | MIT | [LICENSE](licenses/anyio-license.txt) |
| certifi | 2026.7.22 | MPL-2.0 | [LICENSE](licenses/certifi-license.txt) |
| cffi | 2.0.0 | MIT | [LICENSE](licenses/cffi-license.txt) |
| click | 8.1.8 | See license text | [LICENSE.txt](licenses/click-license.txt.txt) |
| colorama | 0.4.6 | See license text | [LICENSE.txt](licenses/colorama-license.txt.txt) |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | [LICENSE](licenses/cryptography-license.txt), [Apache](licenses/cryptography-license.apache.txt), [BSD](licenses/cryptography-license.bsd.txt) |
| defusedxml | 0.7.1 | PSFL | [LICENSE](licenses/defusedxml-license.txt) |
| distro | 1.9.0 | Apache License, Version 2.0 | [LICENSE](licenses/distro-license.txt) |
| exceptiongroup | 1.3.1 | See license text | [LICENSE](licenses/exceptiongroup-license.txt) |
| fastapi | 0.128.8 | MIT | [LICENSE](licenses/fastapi-license.txt) |
| h11 | 0.16.0 | MIT | [LICENSE.txt](licenses/h11-license.txt.txt) |
| httpcore | 1.0.9 | BSD-3-Clause | [LICENSE.md](licenses/httpcore-license.md.txt) |
| httpx | 0.28.1 | BSD-3-Clause | [LICENSE.md](licenses/httpx-license.md.txt) |
| idna | 3.20 | BSD-3-Clause | [LICENSE.md](licenses/idna-license.md.txt) |
| jiter | 0.16.0 | MIT | [LICENSE](licenses/jiter-license.txt) |
| openai | 2.48.0 | Apache-2.0 | [LICENSE](licenses/openai-license.txt) |
| pydantic | 2.13.5 | MIT | [LICENSE](licenses/pydantic-license.txt) |
| pydantic_core | 2.46.5 | MIT | [LICENSE](licenses/pydantic-core-license.txt) |
| pycparser | 2.23 | BSD-3-Clause | [LICENSE](licenses/pycparser-license.txt) |
| python-dotenv | 1.2.2 | BSD-3-Clause | [LICENSE](licenses/python-dotenv-license.txt) |
| sniffio | 1.3.1 | MIT OR Apache-2.0 | [LICENSE](licenses/sniffio-license.txt), [LICENSE.APACHE2](licenses/sniffio-license.apache2.txt), [LICENSE.MIT](licenses/sniffio-license.mit.txt) |
| starlette | 0.49.3 | BSD-3-Clause | [LICENSE.md](licenses/starlette-license.md.txt) |
| tqdm | 4.70.1 | MPL-2.0 AND MIT | [LICENCE](licenses/tqdm-licence.txt) |
| typing-inspection | 0.4.2 | MIT | [LICENSE](licenses/typing-inspection-license.txt) |
| typing_extensions | 4.16.0 | PSF-2.0 | [LICENSE](licenses/typing-extensions-license.txt) |
| uvicorn | 0.39.0 | BSD-3-Clause | [LICENSE.md](licenses/uvicorn-license.md.txt) |

Versions match `requirements.lock.txt`. Package metadata and included license files are the basis of this inventory; recheck additions and updates before redistribution.

## Windows installer/runtime

The Windows installer additionally bundles CPython 3.12 and the PyInstaller bootloader. The exact runtime/build versions and source commit are recorded in the installed `BUILD-INFO.json`. Full Python and PyInstaller license texts (including PyInstaller's bootloader exception) are bundled in the installed `licenses` folder. Installer construction uses NSIS with zlib compression; its full license text is preserved there as well. NSIS, PyInstaller, and compiler tools are build dependencies, while Python and application runtime dependencies are included for users. These component licenses do not select a license for the original project code.

## Optional browser-check tooling

Playwright and playwright-core **1.60.0** are development-only dependencies pinned in `package-lock.json`, under Apache-2.0. They are not needed by, or bundled into, the standalone HTML. Preserved texts: [Playwright license](licenses/playwright-license.txt), [notice](licenses/playwright-notice.txt), [third-party notices](licenses/playwright-third-party-notices.txt), [playwright-core license](licenses/playwright-core-license.txt), [notice](licenses/playwright-core-notice.txt), and [third-party notices](licenses/playwright-core-third-party-notices.txt). Browser executables installed for checks have their own included notices and are not redistributed in project packages.
