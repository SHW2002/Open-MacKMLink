# Third-party components

The portable assistant includes Python 3.12 and its standard library, Tcl/Tk 8.6,
and the PyInstaller bootloader. Their license texts accompany the package in
`licenses/`. The helper code adds a graphical interface, installation discovery,
version checks, isolated patch generation, native validation and runtime/startup
selection. It does not modify the Python, Tcl/Tk or PyInstaller source code.

Sources:

- Python: https://www.python.org/ — `licenses/Python-LICENSE.txt`
- Tcl 8.6.12: https://github.com/tcltk/tcl/blob/core-8-6-12/license.terms — `licenses/Tcl-license.terms`
- Tk 8.6.12: https://www.tcl.tk/ — `licenses/Tk-license.terms`
- PyInstaller 6.16.0: https://github.com/pyinstaller/pyinstaller/tree/v6.16.0 — `licenses/PyInstaller-COPYING.txt`

PyInstaller's GPL includes an exception for distributing applications built
with its bootloader; the complete terms are in the included COPYING text.
Build-only dependencies are pinned in `src/release/requirements.txt` and are
not intentionally packaged as application modules.

Windows and .NET Framework are operating-system prerequisites. Microsoft Visual
C++ runtime DLLs collected from the Python installation retain their Microsoft
terms: https://visualstudio.microsoft.com/license-terms/vs2022-cruntime/.

No vendor MacKMLink executable or runtime assets are included in this download.
The assistant requires an existing installation on the user's computer and
creates a local copy for repair. Vendor software retains its original terms.
This notice does not grant a new license to the vendor software or the project.
