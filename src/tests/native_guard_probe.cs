using System;
using System.Runtime.InteropServices;
public static class NativeGuardProbe {
    public static int Main(string[] args) {
        try {
            Console.OutputEncoding = new System.Text.UTF8Encoding(false);
            string hex = args[0];
            byte[] guard = new byte[hex.Length / 2];
            for (int i=0;i<guard.Length;i++) guard[i]=Convert.ToByte(hex.Substring(i*2,2),16);
            Console.WriteLine(Run(guard));
            return 0;
        } catch (Exception error) { Console.Error.WriteLine(error); return 1; }
    }

    [DllImport("kernel32.dll", SetLastError=true)]
    static extern IntPtr VirtualAlloc(IntPtr address, UIntPtr size, uint allocation, uint protection);
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool VirtualProtect(IntPtr address, UIntPtr size, uint protection, out uint previous);
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool VirtualFree(IntPtr address, UIntPtr size, uint type);
    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    delegate int Probe(int handle, int bitmapObject);

    static void PutInt(byte[] bytes, int offset, int value) {
        Array.Copy(BitConverter.GetBytes(value), 0, bytes, offset, 4);
    }
    static void Check(Probe probe, IntPtr counter, int handle, int bitmapObject, int expected, int calls) {
        Marshal.WriteInt32(counter, 0);
        int actual = probe(handle, bitmapObject);
        if (actual != expected || Marshal.ReadInt32(counter) != calls)
            throw new InvalidOperationException("Guard outcome or FromHandle call count was wrong.");
    }
    public static string Run(byte[] productionGuard) {
        if (IntPtr.Size != 4 || productionGuard.Length != 29)
            throw new InvalidOperationException("Expected the 29-byte x86 production guard.");
        IntPtr buffer = VirtualAlloc(IntPtr.Zero, (UIntPtr)8192, 0x3000, 0x04);
        if (buffer == IntPtr.Zero) throw new InvalidOperationException("VirtualAlloc failed.");
        try {
            byte[] code = new byte[4096];
            // Wrapper preserves ESI and supplies GetClipboardData / FromHandle outcomes.
            byte[] wrapper = {0x56,0x8b,0x44,0x24,0x08,0x8b,0x54,0x24,0x0c,0xe8,0,0,0,0,0x5e,0xc3};
            PutInt(wrapper,10,0x100-14);
            Array.Copy(wrapper,code,wrapper.Length);
            byte[] guard = (byte[])productionGuard.Clone();
            // Relocate only branch operands to the controlled probe functions.
            PutInt(guard,6,0x400-(0x100+10));
            PutInt(guard,12,0x300-(0x100+16));
            PutInt(guard,20,0x400-(0x100+24));
            PutInt(guard,25,0x380-(0x100+29));
            Array.Copy(guard,0,code,0x100,guard.Length);
            IntPtr counter = new IntPtr(buffer.ToInt32()+4096);
            byte[] fromHandle = {0xff,0x05,0,0,0,0,0x8b,0xc2,0xc2,0x04,0x00};
            PutInt(fromHandle,2,counter.ToInt32());
            Array.Copy(fromHandle,0,code,0x300,fromHandle.Length);
            byte[] resume = {0xb8,0x01,0,0,0,0xc3};
            byte[] fallback = {0x31,0xc0,0xc3};
            Array.Copy(resume,0,code,0x380,resume.Length);
            Array.Copy(fallback,0,code,0x400,fallback.Length);
            Marshal.Copy(code,0,buffer,code.Length);
            uint old;
            if (!VirtualProtect(buffer,(UIntPtr)4096,0x20,out old))
                throw new InvalidOperationException("VirtualProtect failed.");
            Probe probe = (Probe)Marshal.GetDelegateForFunctionPointer(buffer,typeof(Probe));
            for (int i=0;i<10000;i++) {
                Check(probe,counter,0,0x1234,0,0);
                Check(probe,counter,0x5678,0,0,1);
                Check(probe,counter,0x5678,0x1234,1,1);
            }
            GC.KeepAlive(probe);
            return "{\"architecture\":\"x86\",\"native_cases\":3,\"executions\":30000,\"passed\":true}";
        } finally { VirtualFree(buffer,UIntPtr.Zero,0x8000); }
    }
}
