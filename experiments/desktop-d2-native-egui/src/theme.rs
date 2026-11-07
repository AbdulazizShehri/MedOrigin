// MedOrigin native design tokens. Local presentation only: no remote fonts,
// assets, telemetry or network. One source of truth for colour, type and
// spacing so screens stop hard-coding RGB values.

use eframe::egui::{self, Color32, CornerRadius, FontId, Stroke, TextStyle, Theme, Visuals};

/// Brand orange from the accepted MedOrigin mark.
pub const BRAND_ORANGE: Color32 = Color32::from_rgb(236, 112, 69);
/// Brand ink used for the mark's internal pillars.
pub const BRAND_INK: Color32 = Color32::from_rgb(17, 19, 22);

/// Semantic colour tokens for one appearance.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Palette {
    pub canvas: Color32,
    pub surface: Color32,
    pub surface_raised: Color32,
    pub border: Color32,
    pub text: Color32,
    pub text_muted: Color32,
    pub accent: Color32,
    pub accent_text: Color32,
    pub selection: Color32,
    pub warning: Color32,
    pub danger: Color32,
    pub success: Color32,
}

pub const DARK: Palette = Palette {
    canvas: Color32::from_rgb(16, 18, 23),
    surface: Color32::from_rgb(22, 25, 31),
    surface_raised: Color32::from_rgb(31, 35, 42),
    border: Color32::from_rgb(46, 51, 60),
    text: Color32::from_rgb(232, 232, 233),
    text_muted: Color32::from_rgb(163, 169, 178),
    accent: BRAND_ORANGE,
    accent_text: Color32::from_rgb(244, 150, 112),
    selection: Color32::from_rgb(133, 71, 49),
    warning: Color32::from_rgb(234, 182, 76),
    danger: Color32::from_rgb(240, 113, 113),
    success: Color32::from_rgb(98, 196, 136),
};

pub const LIGHT: Palette = Palette {
    canvas: Color32::from_rgb(249, 249, 247),
    surface: Color32::from_rgb(255, 255, 255),
    surface_raised: Color32::from_rgb(241, 241, 238),
    border: Color32::from_rgb(218, 218, 213),
    text: Color32::from_rgb(23, 24, 28),
    text_muted: Color32::from_rgb(88, 93, 102),
    accent: Color32::from_rgb(196, 78, 38),
    accent_text: Color32::from_rgb(170, 64, 28),
    selection: Color32::from_rgb(250, 211, 193),
    warning: Color32::from_rgb(146, 88, 6),
    danger: Color32::from_rgb(180, 30, 30),
    success: Color32::from_rgb(22, 120, 58),
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

/// Type scale (logical points).
pub mod size {
    pub const CAPTION: f32 = 12.0;
    pub const BODY: f32 = 14.0;
    pub const BUTTON: f32 = 14.0;
    pub const TITLE: f32 = 17.0;
    pub const HEADING: f32 = 22.0;
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
    v.faint_bg_color = p.surface_raised;
    v.override_text_color = Some(p.text);
    v.hyperlink_color = p.accent_text;
    v.warn_fg_color = p.warning;
    v.error_fg_color = p.danger;
    v.selection.bg_fill = p.selection;
    v.selection.stroke = Stroke::new(1.0, p.accent);
    let radius = CornerRadius::same(6);
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
    v.widgets.inactive.bg_fill = p.surface_raised;
    // Unselected radios, checkboxes and fields need a visible outline.
    v.widgets.inactive.bg_stroke = Stroke::new(1.0, p.border);
    v.widgets.inactive.fg_stroke.color = p.text_muted;
    v.widgets.inactive.weak_bg_fill = p.surface_raised;
    v.widgets.hovered.weak_bg_fill = p.surface_raised;
    v.widgets.hovered.bg_stroke = Stroke::new(1.0, p.accent);
    v.widgets.active.bg_stroke = Stroke::new(1.5, p.accent);
    // Visible keyboard focus ring for accessibility.
    v.widgets.hovered.fg_stroke.color = p.text;
    v.window_corner_radius = CornerRadius::same(8);
    style.visuals = v;
    style.spacing.item_spacing = egui::vec2(space::SM + 1.0, space::SM + 1.0);
    style.spacing.button_padding = egui::vec2(space::MD, space::SM);
    style.spacing.interact_size.y = 28.0;
    style.text_styles = [
        (TextStyle::Heading, FontId::proportional(size::HEADING)),
        (TextStyle::Body, FontId::proportional(size::BODY)),
        (TextStyle::Button, FontId::proportional(size::BUTTON)),
        (TextStyle::Small, FontId::proportional(size::CAPTION)),
        (TextStyle::Monospace, FontId::monospace(13.0)),
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

/// Paint the MedOrigin mark (warm disc with three ink pillars).
pub fn paint_mark(ui: &mut egui::Ui, diameter: f32) -> egui::Response {
    let (rect, response) =
        ui.allocate_exact_size(egui::vec2(diameter, diameter), egui::Sense::hover());
    let c = rect.center();
    let s = diameter / 42.0;
    let painter = ui.painter();
    painter.circle_filled(c, 19.0 * s, BRAND_ORANGE);
    for (dx, length) in [(-9.0, 17.0), (0.0, 23.0), (9.0, 17.0)] {
        painter.rect_filled(
            egui::Rect::from_center_size(
                egui::pos2(c.x + dx * s, c.y),
                egui::vec2(5.5 * s, length * s),
            ),
            2.0 * s,
            BRAND_INK,
        );
    }
    response
}

/// Small rounded status chip, e.g. "Fictional data only".
pub fn chip(ui: &mut egui::Ui, text: &str, color: Color32) -> egui::Response {
    egui::Frame::new()
        .stroke(Stroke::new(1.0, color))
        .corner_radius(CornerRadius::same(10))
        .inner_margin(egui::Margin::symmetric(8, 2))
        .show(ui, |ui| {
            ui.label(egui::RichText::new(text).size(size::CAPTION).color(color))
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
            for bg in [p.canvas, p.surface, p.surface_raised] {
                assert!(contrast(p.text, bg) >= 7.0, "body text {bg:?}");
                for fg in [p.text_muted, p.accent_text, p.warning, p.danger, p.success] {
                    assert!(contrast(fg, bg) >= 4.5, "{fg:?} on {bg:?}");
                }
            }
        }
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
