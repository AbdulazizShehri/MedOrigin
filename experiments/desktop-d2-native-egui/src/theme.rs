// MedOrigin native design tokens. Local presentation only: no remote fonts,
// assets, telemetry or network. Colours come from the owner-approved design
// contract `docs/design/desktop-v1/tokens.json` (checked by a test below) plus
// the tag colours of the "Desktop — Encounter review" board.

use eframe::egui::{self, Color32, CornerRadius, FontId, Stroke, TextStyle, Theme, Visuals};

/// Origin Orange (`brand.orange`).
pub const BRAND_ORANGE: Color32 = Color32::from_rgb(0xFE, 0x68, 0x1B);

/// Semantic colour tokens for one appearance.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Palette {
    pub canvas: Color32,
    pub sidebar: Color32,
    pub surface: Color32,
    pub raised: Color32,
    pub hover: Color32,
    pub border: Color32,
    pub border_strong: Color32,
    pub text: Color32,
    pub text_secondary: Color32,
    pub text_muted: Color32,
    pub accent: Color32,
    pub accent_hover: Color32,
    pub on_accent: Color32,
    pub focus: Color32,
    pub selection: Color32,
    pub success: Color32,
    pub warning: Color32,
    pub danger: Color32,
    pub badge: Color32,
    // Board tag colours: Gated/Synthetic (pink), Experiment/source (blue),
    // verified lineage (mint).
    pub pink_bg: Color32,
    pub pink_text: Color32,
    pub blue_bg: Color32,
    pub blue_text: Color32,
    pub mint_bg: Color32,
    pub mint_text: Color32,
}

const fn hex(v: u32) -> Color32 {
    Color32::from_rgb((v >> 16) as u8, (v >> 8) as u8, v as u8)
}

pub const LIGHT: Palette = Palette {
    canvas: hex(0xF6F7F4),
    sidebar: hex(0xEEF1EE),
    surface: hex(0xFFFFFF),
    raised: hex(0xF9FAF8),
    hover: hex(0xE9EEEA),
    border: hex(0xD7DED8),
    border_strong: hex(0xBAC5BD),
    text: hex(0x19211C),
    text_secondary: hex(0x41544A),
    text_muted: hex(0x57675D),
    accent: hex(0xC94A05),
    accent_hover: hex(0xAD3E00),
    on_accent: hex(0xFFFFFF),
    focus: hex(0xA13C04),
    selection: hex(0xFFE5D6),
    success: hex(0x176A50),
    warning: hex(0x775200),
    danger: hex(0xA52E30),
    badge: hex(0xE9EFEA),
    pink_bg: hex(0xFFE3F5),
    pink_text: hex(0x6B1F52),
    blue_bg: hex(0xDDF0FF),
    blue_text: hex(0x0E4A73),
    mint_bg: hex(0xE3F7E1),
    mint_text: hex(0x1E5A26),
};

pub const DARK: Palette = Palette {
    canvas: hex(0x0D0F10),
    sidebar: hex(0x121516),
    surface: hex(0x181C1D),
    raised: hex(0x202526),
    hover: hex(0x272D2E),
    border: hex(0x31383A),
    border_strong: hex(0x455052),
    text: hex(0xF4F5F2),
    text_secondary: hex(0xBEC7C2),
    text_muted: hex(0xA6B0AA),
    accent: hex(0xFF8A45),
    accent_hover: hex(0xFFAB73),
    on_accent: hex(0x171818),
    focus: hex(0xFFB27E),
    selection: hex(0x3D2C21),
    success: hex(0x86DFC0),
    warning: hex(0xF2D398),
    danger: hex(0xFFA2A2),
    badge: hex(0x262D2A),
    pink_bg: hex(0x3A2633),
    pink_text: hex(0xFFC2EA),
    blue_bg: hex(0x1C2F3D),
    blue_text: hex(0xA6DBFF),
    mint_bg: hex(0x1F3222),
    mint_text: hex(0xC3F0BF),
};

pub fn palette(theme: Theme) -> &'static Palette {
    match theme {
        Theme::Dark => &DARK,
        Theme::Light => &LIGHT,
    }
}

/// Spacing scale (logical points).
pub mod space {
    pub const XS: f32 = 4.0;
    pub const SM: f32 = 8.0;
    pub const MD: f32 = 12.0;
    pub const LG: f32 = 16.0;
    pub const XL: f32 = 24.0;
}

/// Type scale from `tokens.json` typography (logical points).
pub mod size {
    pub const CAPTION: f32 = 11.0;
    pub const SMALL: f32 = 12.0;
    pub const BODY: f32 = 13.0;
    pub const COMFORTABLE: f32 = 14.0;
    pub const TITLE: f32 = 16.0;
    pub const HEADING: f32 = 22.0;
}

/// Layout from `tokens.json` layout (logical points).
pub mod layout {
    pub const SIDEBAR: f32 = 244.0;
    pub const HEADER: f32 = 52.0;
    pub const INSPECTOR: f32 = 320.0;
}

fn style_for(theme: Theme, base: &egui::Style) -> egui::Style {
    let p = palette(theme);
    let mut style = base.clone();
    let mut v = match theme {
        Theme::Dark => Visuals::dark(),
        Theme::Light => Visuals::light(),
    };
    v.panel_fill = p.canvas;
    v.window_fill = p.surface;
    v.window_stroke = Stroke::new(1.0, p.border);
    v.extreme_bg_color = p.surface;
    v.faint_bg_color = p.raised;
    v.override_text_color = Some(p.text);
    v.hyperlink_color = p.accent;
    v.warn_fg_color = p.warning;
    v.error_fg_color = p.danger;
    v.selection.bg_fill = p.selection;
    v.selection.stroke = Stroke::new(1.0, p.text);
    let radius = CornerRadius::same(8);
    for w in [
        &mut v.widgets.noninteractive,
        &mut v.widgets.inactive,
        &mut v.widgets.hovered,
        &mut v.widgets.active,
        &mut v.widgets.open,
    ] {
        w.corner_radius = radius;
    }
    v.widgets.noninteractive.bg_stroke = Stroke::new(1.0, p.border);
    v.widgets.noninteractive.fg_stroke.color = p.text;
    v.widgets.inactive.bg_fill = p.surface;
    v.widgets.inactive.weak_bg_fill = p.surface;
    // Unselected radios, checkboxes and fields need a visible outline.
    v.widgets.inactive.bg_stroke = Stroke::new(1.0, p.border);
    v.widgets.inactive.fg_stroke.color = p.text;
    v.widgets.hovered.bg_fill = p.hover;
    v.widgets.hovered.weak_bg_fill = p.hover;
    v.widgets.hovered.bg_stroke = Stroke::new(1.0, p.border_strong);
    v.widgets.hovered.fg_stroke.color = p.text;
    v.widgets.active.bg_fill = p.hover;
    v.widgets.active.weak_bg_fill = p.hover;
    // Visible keyboard focus ring in the design's focus colour.
    v.widgets.active.bg_stroke = Stroke::new(2.0, p.focus);
    v.widgets.open.weak_bg_fill = p.hover;
    v.window_corner_radius = CornerRadius::same(12);
    style.visuals = v;
    style.spacing.item_spacing = egui::vec2(space::SM, space::SM);
    style.spacing.button_padding = egui::vec2(14.0, 6.0);
    style.spacing.interact_size.y = 30.0;
    style.text_styles = [
        (TextStyle::Heading, FontId::proportional(size::HEADING)),
        (TextStyle::Body, FontId::proportional(size::BODY)),
        (TextStyle::Button, FontId::proportional(size::BODY)),
        (TextStyle::Small, FontId::proportional(size::CAPTION)),
        (TextStyle::Monospace, FontId::monospace(12.5)),
    ]
    .into();
    style
}

/// Install MedOrigin styles for both appearances and apply a preference.
pub fn install(ctx: &egui::Context, preference: egui::ThemePreference) {
    for theme in [Theme::Dark, Theme::Light] {
        let base = (*ctx.style_of(theme)).clone();
        ctx.set_style_of(theme, style_for(theme, &base));
    }
    ctx.set_theme(preference);
}

// Lineage identity, rasterised from the committed SVGs in
// docs/design/desktop-v1/identity-lineage/svg (see assets/lineage/MANIFEST.txt).
// The mark is never redrawn in code.
const MARK_PX: usize = 112;
const MARK_LIGHT: &[u8] = include_bytes!("../assets/lineage/lineage-mark-112.rgba");
const MARK_DARK: &[u8] = include_bytes!("../assets/lineage/lineage-mark-on-dark-112.rgba");
pub const APP_ICON_PX: u32 = 256;
pub const APP_ICON_RGBA: &[u8] = include_bytes!("../assets/lineage/lineage-app-icon-dark-256.rgba");

fn mark_texture(ctx: &egui::Context, theme: Theme) -> egui::TextureHandle {
    let id = egui::Id::new(("medorigin-lineage-mark", theme == Theme::Dark));
    if let Some(handle) = ctx.data(|d| d.get_temp::<egui::TextureHandle>(id)) {
        return handle;
    }
    let bytes = if theme == Theme::Dark {
        MARK_DARK
    } else {
        MARK_LIGHT
    };
    let image = egui::ColorImage::from_rgba_unmultiplied([MARK_PX, MARK_PX], bytes);
    let handle = ctx.load_texture(
        "medorigin-lineage-mark",
        image,
        egui::TextureOptions::LINEAR,
    );
    ctx.data_mut(|d| d.insert_temp(id, handle.clone()));
    handle
}

/// The Lineage mark for the current appearance (decorative; the product
/// name is always shown next to it as text).
pub fn mark(ui: &mut egui::Ui, size: f32) -> egui::Response {
    let texture = mark_texture(ui.ctx(), ui.ctx().theme());
    ui.add(egui::Image::new((texture.id(), egui::vec2(size, size))))
}

/// Small filled tag, e.g. "Gated" or "Synthetic".
pub fn tag(ui: &mut egui::Ui, text: &str, bg: Color32, fg: Color32) -> egui::Response {
    egui::Frame::new()
        .fill(bg)
        .corner_radius(CornerRadius::same(4))
        .inner_margin(egui::Margin::symmetric(6, 1))
        .show(ui, |ui| {
            ui.label(
                egui::RichText::new(text)
                    .size(size::CAPTION)
                    .strong()
                    .color(fg),
            )
        })
        .inner
}

/// Card surface used across screens (surface fill, 1px border, 12px radius).
pub fn card<R>(ui: &mut egui::Ui, add: impl FnOnce(&mut egui::Ui) -> R) -> R {
    let p = palette(ui.ctx().theme());
    egui::Frame::new()
        .fill(p.surface)
        .stroke(Stroke::new(1.0, p.border))
        .corner_radius(CornerRadius::same(12))
        .inner_margin(egui::Margin::symmetric(20, 16))
        .show(ui, |ui| {
            ui.set_width(ui.available_width());
            add(ui)
        })
        .inner
}

#[cfg(test)]
mod tests {
    use super::*;

    fn luminance(c: Color32) -> f64 {
        let ch = |v: u8| {
            let v = f64::from(v) / 255.0;
            if v <= 0.039_28 {
                v / 12.92
            } else {
                ((v + 0.055) / 1.055).powf(2.4)
            }
        };
        0.2126 * ch(c.r()) + 0.7152 * ch(c.g()) + 0.0722 * ch(c.b())
    }

    fn contrast(a: Color32, b: Color32) -> f64 {
        let (x, y) = (luminance(a), luminance(b));
        let (hi, lo) = if x > y { (x, y) } else { (y, x) };
        (hi + 0.05) / (lo + 0.05)
    }

    #[test]
    fn text_tokens_meet_wcag_aa_on_every_surface() {
        for p in [&DARK, &LIGHT] {
            for bg in [p.canvas, p.sidebar, p.surface, p.raised] {
                assert!(contrast(p.text, bg) >= 7.0, "body text {bg:?}");
                for fg in [
                    p.text_secondary,
                    p.text_muted,
                    p.success,
                    p.warning,
                    p.danger,
                ] {
                    assert!(contrast(fg, bg) >= 4.5, "{fg:?} on {bg:?}");
                }
            }
            assert!(contrast(p.on_accent, p.accent) >= 4.5, "button label");
            for (fg, bg) in [
                (p.pink_text, p.pink_bg),
                (p.blue_text, p.blue_bg),
                (p.mint_text, p.mint_bg),
                (p.text_muted, p.badge),
                (p.text, p.selection),
            ] {
                assert!(contrast(fg, bg) >= 4.5, "tag {fg:?} on {bg:?}");
            }
        }
    }

    #[test]
    fn palettes_match_the_committed_design_contract() {
        let raw = include_str!("../../../docs/design/desktop-v1/tokens.json");
        let tokens: serde_json::Value = serde_json::from_str(raw).unwrap();
        let rgb = |c: Color32| format!("#{:02X}{:02X}{:02X}", c.r(), c.g(), c.b());
        for (name, p) in [("light", &LIGHT), ("dark", &DARK)] {
            let t = &tokens[name];
            for (key, value) in [
                ("canvas", p.canvas),
                ("sidebar", p.sidebar),
                ("surface", p.surface),
                ("raised", p.raised),
                ("hover", p.hover),
                ("border", p.border),
                ("borderStrong", p.border_strong),
                ("text", p.text),
                ("textSecondary", p.text_secondary),
                ("textMuted", p.text_muted),
                ("accent", p.accent),
                ("accentHover", p.accent_hover),
                ("accentText", p.on_accent),
                ("focus", p.focus),
                ("selection", p.selection),
                ("success", p.success),
                ("warning", p.warning),
                ("danger", p.danger),
                ("badge", p.badge),
            ] {
                assert_eq!(t[key].as_str(), Some(rgb(value).as_str()), "{name}.{key}");
            }
        }
        assert_eq!(tokens["brand"]["orange"].as_str(), Some("#FE681B"));
        assert_eq!(rgb(BRAND_ORANGE), "#FE681B");
        assert_eq!(tokens["layout"]["sidebarPx"], 244);
        assert_eq!(tokens["layout"]["headerPx"], 52);
        assert_eq!(tokens["layout"]["inspectorPx"], 320);
    }

    #[test]
    fn lineage_rasters_come_from_the_committed_svgs() {
        use sha2::{Digest, Sha256};
        let hex = |b: &[u8]| -> String {
            Sha256::digest(b)
                .iter()
                .map(|x| format!("{x:02x}"))
                .collect()
        };
        let manifest = include_str!("../assets/lineage/MANIFEST.txt");
        let svg_dir = concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../docs/design/desktop-v1/identity-lineage/svg/"
        );
        let mut checked = 0;
        for line in manifest.lines() {
            let mut parts = line.split(' ');
            let file = parts.next().unwrap();
            let _dims = parts.next().unwrap();
            let svg_sha = parts.next().unwrap().strip_prefix("svg_sha256=").unwrap();
            let rgba_sha = parts.next().unwrap().strip_prefix("rgba_sha256=").unwrap();
            let stem = file.rsplit_once('-').unwrap().0;
            let svg = std::fs::read(format!("{svg_dir}{stem}.svg")).unwrap();
            assert_eq!(hex(&svg), svg_sha, "{stem}.svg changed: re-rasterise");
            let rgba = match file {
                "lineage-mark-112.rgba" => MARK_LIGHT,
                "lineage-mark-on-dark-112.rgba" => MARK_DARK,
                "lineage-app-icon-dark-256.rgba" => APP_ICON_RGBA,
                other => panic!("unexpected raster {other}"),
            };
            assert_eq!(hex(rgba), rgba_sha, "{file}");
            checked += 1;
        }
        assert_eq!(checked, 3);
        assert_eq!(MARK_LIGHT.len(), MARK_PX * MARK_PX * 4);
        assert_eq!(
            APP_ICON_RGBA.len(),
            (APP_ICON_PX * APP_ICON_PX * 4) as usize
        );
    }

    #[test]
    fn install_sets_both_appearances_without_changing_preference_semantics() {
        let ctx = egui::Context::default();
        install(&ctx, egui::ThemePreference::Light);
        assert_eq!(ctx.theme(), Theme::Light);
        assert_eq!(ctx.style_of(Theme::Light).visuals.panel_fill, LIGHT.canvas);
        assert_eq!(ctx.style_of(Theme::Dark).visuals.panel_fill, DARK.canvas);
    }
}
