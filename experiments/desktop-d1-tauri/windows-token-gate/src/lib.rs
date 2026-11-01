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

/// The three well-known Windows network capability SIDs must all be absent.
/// Other capabilities may be required for desktop UI integration.
#[inline]
fn reject_network_capability_bits(bits: u8) -> Result<(), &'static str> {
    if bits == 0 { Ok(()) } else { Err("primary_token_has_network_capability") }
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
        fn EqualSid(first: *const c_void, second: *const c_void) -> i32;
    }

    #[repr(C)]
    struct SidAndAttributes { sid: *mut c_void, attributes: u32 }
    #[repr(C)]
    struct TokenGroups { count: u32, groups: [SidAndAttributes; 1] }
    #[repr(C, align(4))]
    struct SidBytes([u8;16]);
    // Source: Microsoft capability SIDs S-1-15-3-1/-2/-3.
    static INTERNET_CLIENT: SidBytes = SidBytes([1,2,0,0,0,0,0,15,3,0,0,0,1,0,0,0]);
    static INTERNET_CLIENT_SERVER: SidBytes = SidBytes([1,2,0,0,0,0,0,15,3,0,0,0,2,0,0,0]);
    static PRIVATE_NETWORK_CLIENT_SERVER: SidBytes = SidBytes([1,2,0,0,0,0,0,15,3,0,0,0,3,0,0,0]);

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
        super::classify_appcontainer_bit(value != 0)?;
        // TokenCapabilities = 30. Query the primary token's TOKEN_GROUPS
        // from the Windows kernel; never trust launch arguments or env vars.
        let mut required = 0u32;
        unsafe { GetTokenInformation(handle, 30, core::ptr::null_mut(), 0, &mut required); }
        if !(4..=65536).contains(&required) {
            return Err("primary_token_capability_size_invalid");
        }
        // DWORD-aligned TOKEN_GROUPS, pointer-aligned SID_AND_ATTRIBUTES.
        let mut buffer = vec![0u64; (required as usize + 7) / 8];
        let mut got = 0u32;
        if unsafe {
            GetTokenInformation(handle, 30, buffer.as_mut_ptr().cast(), required, &mut got)
        } == 0 || got < 4 || got > required {
            return Err("primary_token_capability_query_failed");
        }
        let count = u32::from_ne_bytes(buffer[0].to_ne_bytes()[..4].try_into()
            .map_err(|_| "primary_token_capability_count_invalid")?) as usize;
        if count > 1024 {
            return Err("primary_token_capability_count_invalid");
        }
        let offset = core::mem::offset_of!(TokenGroups, groups);
        let item = core::mem::size_of::<SidAndAttributes>();
        let needed = offset.checked_add(count.checked_mul(item)
            .ok_or("primary_token_capability_buffer_invalid")?)
            .ok_or("primary_token_capability_buffer_invalid")?;
        if needed > got as usize {
            return Err("primary_token_capability_buffer_invalid");
        }
        let entries = unsafe { (buffer.as_ptr() as *const u8).add(offset)
            .cast::<SidAndAttributes>() };
        let network = [&INTERNET_CLIENT, &INTERNET_CLIENT_SERVER,
            &PRIVATE_NETWORK_CLIENT_SERVER];
        let mut network_bits = 0u8;
        for i in 0..count {
            let sid = unsafe { (*entries.add(i)).sid };
            if sid.is_null() {
                return Err("primary_token_null_capability_sid");
            }
            for (j, expected) in network.iter().enumerate() {
                if unsafe { EqualSid(sid, expected.0.as_ptr().cast()) } != 0 {
                    network_bits |= 1u8 << j;
                }
            }
        }
        super::reject_network_capability_bits(network_bits)
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

    #[test]
    fn known_internet_and_private_network_capabilities_each_fail_closed() {
        for bits in [1u8, 2, 4, 3, 5, 6, 7] {
            assert_eq!(super::reject_network_capability_bits(bits),
                Err("primary_token_has_network_capability"));
        }
        assert!(super::reject_network_capability_bits(0).is_ok());
    }
}
