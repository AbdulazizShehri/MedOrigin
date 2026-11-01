// NONPUBLISHING, SYNTHETIC ONLY: read-only token containment experiment.
// This is an independent Windows native probe, NOT part of the D1 app.
// No network, PHI, privilege elevation, process inspection or config changes.
#![cfg_attr(not(windows), allow(dead_code))]
#[cfg(windows)]
mod win {
    use std::ffi::c_void;
    #[link(name="kernel32")]
    unsafe extern "system" {
        fn GetCurrentProcess() -> isize;
        fn CloseHandle(handle:isize) -> i32;
        fn IsProcessInJob(process:isize, job:isize, result:*mut i32) -> i32;
    }
    #[link(name="advapi32")]
    unsafe extern "system" {
        fn OpenProcessToken(process:isize, access:u32, token:*mut isize) -> i32;
        fn GetTokenInformation(token:isize, class:u32, info:*mut c_void, len:u32, returned:*mut u32) -> i32;
    }
    struct OwnedToken(isize);
    impl Drop for OwnedToken {
        fn drop(&mut self){unsafe{CloseHandle(self.0);}}
    }
    pub fn run() -> Result<(),&'static str> {
        let process=unsafe{GetCurrentProcess()};
        let mut token=0isize;
        // TOKEN_QUERY=0x0008, TokenIsAppContainer=29 (Windows SDK).
        if unsafe{OpenProcessToken(process,0x0008,&mut token)}==0||token==0 {
            return Err("D1_TOKEN_PROBE_OPEN_NO_GO");
        }
        let _guard=OwnedToken(token);
        let mut is_container=0u32;
        let mut returned=0u32;
        if unsafe{GetTokenInformation(token,29,(&mut is_container as *mut u32).cast(),4,&mut returned)}==0||returned!=4 {
            return Err("D1_TOKEN_PROBE_TOKEN_INFORMATION_NO_GO");
        }
        let mut in_any_job=0i32;
        if unsafe{IsProcessInJob(process,0,&mut in_any_job)}==0 {
            return Err("D1_TOKEN_PROBE_JOB_QUERY_NO_GO");
        }
        println!("D1_TOKEN_PROBE_COMPLETE APPCONTAINER={} ANY_JOB={}",u8::from(is_container!=0),u8::from(in_any_job!=0));
        Ok(())
    }
}
fn main(){
    #[cfg(windows)]
    if let Err(message)=win::run(){eprintln!("{message}");std::process::exit(2);}
    #[cfg(not(windows))]
    {eprintln!("D1_TOKEN_PROBE_WINDOWS_ONLY");std::process::exit(2);}
}
