// NONPUBLISHING Windows read-only capability count probe.
// TokenCapabilities=30 (TOKEN_GROUPS), TokenIsAppContainer=29.
// Observe actual primary-token capability count on ordinary host vs MXC.
// Never use these observations as stand-alone packet-denial attestation.
#[cfg(windows)]
mod win {
    use core::ffi::c_void;
    #[link(name="kernel32")]
    unsafe extern "system" {
        fn GetCurrentProcess() -> isize;
        fn CloseHandle(handle: isize) -> i32;
    }
    #[link(name="advapi32")]
    unsafe extern "system" {
        fn OpenProcessToken(process: isize, access: u32, token: *mut isize) -> i32;
        fn GetTokenInformation(token: isize, class: u32, value: *mut c_void, length: u32, returned: *mut u32) -> i32;
    }
    struct Token(isize);
    impl Drop for Token {fn drop(&mut self){unsafe {CloseHandle(self.0);}}}
    fn run() -> Result<(u32,u32), &'static str> {
        let mut raw=0isize;
        if unsafe {OpenProcessToken(unsafe{GetCurrentProcess()},0x0008,&mut raw)}==0||raw==0 {
            return Err("D1_CAPABILITIES_TOKEN_OPEN_NO_GO");
        }
        let _token=Token(raw);
        let mut app=0u32;let mut returned=0u32;
        if unsafe {GetTokenInformation(raw,29,(&mut app as *mut u32).cast(),4,&mut returned)}==0||returned!=4 {
            return Err("D1_CAPABILITIES_APPCONTAINER_QUERY_NO_GO");
        }
        let mut needed=0u32;
        // Probe the size of TOKEN_GROUPS; 0 capabilities still requires a header.
        unsafe {GetTokenInformation(raw,30,core::ptr::null_mut(),0,&mut needed);}
        if needed<4||needed>65536 {return Err("D1_CAPABILITIES_BUFFER_SIZE_NO_GO");}
        let mut buffer=vec![0u64;(needed as usize+7)/8];
        let mut got=0u32;
        if unsafe {GetTokenInformation(raw,30,buffer.as_mut_ptr().cast(),needed,&mut got)}==0||got<4||got>needed {
            return Err("D1_CAPABILITIES_QUERY_NO_GO");
        }
        // First DWORD of TOKEN_GROUPS is GroupCount. Memory is u64-aligned.
        let groups=u32::from_ne_bytes(buffer[0].to_ne_bytes()[..4].try_into().unwrap());
        if groups>1024 {return Err("D1_CAPABILITIES_IMPLAUSIBLE_COUNT");}
        Ok((app,groups))
    }
    pub(super) fn main() {
        match run() {
            Ok((app,groups))=>println!("D1_CAPABILITY_PROBE_COMPLETE APPCONTAINER={} TOKEN_CAPABILITIES_COUNT={}",u8::from(app!=0),groups),
            Err(e)=>{eprintln!("{e}");std::process::exit(2)}
        }
    }
}
fn main() {
    #[cfg(windows)] win::main();
    #[cfg(not(windows))] {eprintln!("D1_CAPABILITIES_WINDOWS_ONLY");std::process::exit(2)}
}
