//! Report-an-issue support. Builds a sanitized, user-reviewable diagnostics
//! summary. Nothing is sent anywhere: the user copies the text and opens the
//! issue page themselves. No paths, usernames, env vars or workspace data.

/// Public issue form. Shown as text only; the app never opens a connection.
pub const ISSUE_FORM: &str =
    "github.com/AbdulazizShehri/MedOrigin/issues/new?template=desktop_bug_report.yml";

pub const APP_VERSION: &str = env!("CARGO_PKG_VERSION");

/// Release channel shown to users. This build is a developer candidate that
/// only admits fictional data; it must never be described as clinical.
pub const CHANNEL: &str = "Developer candidate (fictional data only)";

/// Allowlisted fields only. `mode` must be one of the app's static status
/// strings so no user-entered text can leak into the summary.
pub fn diagnostics_summary(mode: &'static str, appearance: &'static str) -> String {
    format!(
        "MedOrigin Desktop {APP_VERSION}\n\
         Channel: {CHANNEL}\n\
         OS: {} ({})\n\
         Session mode: {mode}\n\
         Appearance: {appearance}\n\
         Network access: none (offline build)\n\
         Logs attached: no",
        std::env::consts::OS,
        std::env::consts::ARCH,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn summary_contains_only_allowlisted_non_identifying_fields() {
        let text = diagnostics_summary("No connected production Core", "Dark");
        assert!(text.contains(APP_VERSION));
        assert!(text.contains(std::env::consts::OS));
        assert_eq!(text.lines().count(), 7);
        for forbidden in [":\\", "/home/", "/Users/", "@", "USERNAME", "Patient/"] {
            assert!(!text.contains(forbidden), "leaked {forbidden}");
        }
        if let Ok(user) = std::env::var("USERNAME").or_else(|_| std::env::var("USER"))
            && user.len() > 2
        {
            assert!(!text.contains(&user));
        }
    }

    #[test]
    fn issue_form_is_the_canonical_repository_template() {
        assert!(ISSUE_FORM.starts_with("github.com/AbdulazizShehri/MedOrigin/issues/new"));
        assert!(ISSUE_FORM.ends_with("desktop_bug_report.yml"));
    }
}
