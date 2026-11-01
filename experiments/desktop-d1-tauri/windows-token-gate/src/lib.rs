//! Experimental Windows D1 primary-token admission.
//!
//! AppContainer identity is necessary for the selected tested MXC backend,
//! but NOT sufficient to attest MXC provenance, networking policy, WFP
//! enforcement, signing, or production release readiness. This separate crate
//! confines the small Windows FFI surface outside Tauri's unsafe-forbidden code.

#[inline]
fn classify_appcontainer_bit(is_appcontainer: bool) -> Result<(), &'static str> {
    if is_appcontainer { Ok(()) } else { Err("primary_token_not_appcontainer") }
}

#[cfg(windows)]
mod windows {
    use core::ffi::c_void;
    #[link(name = "kernel32")]
    unsafe extern "system" {
        fn GetCurrentProcess() -> isize;
        fn CloseHandle(handle: isize) -> i32;
    }
    #[link(name = "advapi32")]
    unsafe extern "system" {
        fn OpenProcessToken(process: isize, access: u32, token: *mut isize) -> i32;
        fn GetTokenInformation(
            token: isize,
            information_class: u32,
            information: *mut c_void,
            information_size: u32,
            returned_size: *mut u32,
        ) -> i32;
    }

    struct OwnedToken(isize);
    impl Drop for OwnedToken {
        fn drop(&mut self) {
            // Handle obtained only from successful OpenProcessToken.
            unsafe { CloseHandle(self.0); }
        }
    }
    pub(super) fn check() -> Result<(), &'static str> {
        let process = unsafe { GetCurrentProcess() };
        let mut handle = 0isize;
        // TOKEN_QUERY = 0x0008. Query the current *process primary* token,
        // not an impersonation token that could differ per thread.
        if unsafe { OpenProcessToken(process, 0x0008, &mut handle) } == 0 || handle == 0 {
            return Err("process_primary_token_unavailable");
        }
        let _owned = OwnedToken(handle);
        let mut value = 0u32;
        let mut returned = 0u32;
        // TokenIsAppContainer = 29, per the Windows SDK. DWORD result.
        if unsafe {
            GetTokenInformation(
                handle,
                29,
                (&mut value as *mut u32).cast(),
                core::mem::size_of::<u32>() as u32,
                &mut returned,
            )
        } == 0 || returned != core::mem::size_of::<u32>() as u32 {
            return Err("primary_token_appcontainer_query_failed");
        }
        super::classify_appcontainer_bit(value != 0)
    }
}

/// Deny an uncontained Windows D1 launch before Tauri/WebView2 initialization.
///
/// AppContainer token presence is intentionally **not** called MXC attestation.
/// No environment variables or user-provided sentinel can bypass this check.
pub fn require_windows_appcontainer_primary_token() -> Result<(), &'static str> {
    #[cfg(windows)]
    { windows::check() }
    #[cfg(not(windows))]
    { Err("windows_only") }
}

#[cfg(test)]
mod tests {
    #[test]
    fn missing_appcontainer_bit_fails_closed() {
        assert_eq!(
            super::classify_appcontainer_bit(false),
            Err("primary_token_not_appcontainer")
        );
        assert!(super::classify_appcontainer_bit(true).is_ok());
    }
}
