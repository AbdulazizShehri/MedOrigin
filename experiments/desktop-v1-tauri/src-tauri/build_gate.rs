//! Fail-closed packaging policy for a synthetic-only desktop experiment.
//! Any release/custom build profile must be reviewed and explicitly change
//! this source-controlled gate after egress and clinical acceptance.
//! There is deliberately no environment variable or feature flag override.

pub fn enforce_nonreleasable_profile(profile: &str) -> Result<(), &'static str> {
    match profile {
        // Cargo's dev and test profiles expose PROFILE=debug.
        "debug" | "test" => Ok(()),
        // Unknown/custom profiles are also refused; no accidental production
        // bypass via cargo --profile.
        _ => Err(
            "MEDORIGIN_RELEASE_NO_GO: synthetic desktop WebView2 egress unqualified; no release/custom build profile authorized",
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn debug_and_test_are_the_only_permitted_profiles() {
        for profile in ["debug", "test"] {
            assert!(enforce_nonreleasable_profile(profile).is_ok());
        }
    }

    #[test]
    fn release_production_custom_and_unset_profiles_are_refused() {
        for profile in [
            "release",
            "production",
            "custom-release",
            "bench",
            "",
            "Release",
            "DEBUG",
            "dev",
        ] {
            let error = enforce_nonreleasable_profile(profile).unwrap_err();
            assert!(error.contains("MEDORIGIN_RELEASE_NO_GO"));
            assert!(error.contains("egress unqualified"));
        }
    }
}
