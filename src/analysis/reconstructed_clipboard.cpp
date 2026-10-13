// Reconstructed semantics of the verified branch, not the vendor's source.
// The compiled repair is a 29-byte x86 guard emitted by bitmap_guard.py.
#include <windows.h>
#include <afxwin.h>

// Existing application routines are intentionally represented as declarations.
void ConvertAndSynchronizeBitmap(CBitmap* bitmap);
void ContinueWithoutBitmap();

void ReconstructedBitmapBranch()
{
    if (!IsClipboardFormatAvailable(CF_BITMAP)) {
        ContinueWithoutBitmap();
        return;
    }

    // Original code continued even when GetClipboardData returned NULL.
    HBITMAP handle = static_cast<HBITMAP>(GetClipboardData(CF_BITMAP));
    if (!handle) {
        ContinueWithoutBitmap();
        return;
    }

    CBitmap* bitmap = CBitmap::FromHandle(handle);
    if (!bitmap) {
        ContinueWithoutBitmap();
        return;
    }
    ConvertAndSynchronizeBitmap(bitmap);
}

// Caller already owns an open clipboard. Both continuation paths run the
// original object cleanup and CloseClipboard; the repair does not free handles.
