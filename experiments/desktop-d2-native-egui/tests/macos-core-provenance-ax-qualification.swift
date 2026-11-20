import ApplicationServices
import Foundation

// Actual native, source-fixed Core reports GUI exercise; synthetic-only.
// This is an AX interaction test, not a keyboard/VoiceOver qualification.
func refuse(_ reason: String) -> Never {
  fputs("MACOS_CORE_PROVENANCE_AX_NO_GO: \(reason)\n", stderr)
  exit(1)
}
guard CommandLine.arguments.count == 2,
      let pid = Int32(CommandLine.arguments[1]), pid > 0 else {
  refuse("expected source-controlled synthetic D2 PID")
}
guard AXIsProcessTrusted() else { refuse("accessibility inspection unavailable") }
let app = AXUIElementCreateApplication(pid)
var nativeWindow: AXUIElement?
for _ in 0..<40 {
  var value: CFTypeRef?
  if AXUIElementCopyAttributeValue(app, kAXWindowsAttribute as CFString, &value)
    == .success, let windows = value as? [AXUIElement], windows.count == 1
  {
    nativeWindow = windows[0]
    break
  }
  Thread.sleep(forTimeInterval: 0.2)
}
guard let window = nativeWindow else { refuse("one native window absent") }

func stringAttr(_ node: AXUIElement, _ key: CFString) -> String {
  var result: CFTypeRef?
  guard AXUIElementCopyAttributeValue(node, key, &result) == .success else {
    return ""
  }
  return String(describing: result ?? "" as CFTypeRef)
}
struct View {
  let node: AXUIElement
  let role: String
  let words: [String]
}
func collect() -> [View] {
  var result = [View]()
  func visit(_ node: AXUIElement, _ depth: Int) {
    guard depth < 24, result.count < 500 else { return }
    let attrs = [
      stringAttr(node, kAXTitleAttribute as CFString),
      stringAttr(node, kAXValueAttribute as CFString),
      stringAttr(node, kAXDescriptionAttribute as CFString),
    ]
    result.append(View(
      node: node,
      role: stringAttr(node, kAXRoleAttribute as CFString),
      words: attrs
    ))
    var children: CFTypeRef?
    if AXUIElementCopyAttributeValue(node, kAXChildrenAttribute as CFString, &children)
      == .success, let items = children as? [AXUIElement]
    {
      for item in items { visit(item, depth + 1) }
    }
  }
  visit(window, 0)
  return result
}
func find(_ title: String) -> View? {
  collect().first {
    $0.words.contains { $0.contains(title) } &&
      ($0.role.contains("Button") || $0.role.contains("CheckBox") ||
       $0.role.contains("Radio"))
  }
}
func press(_ title: String) {
  var target: View?
  for _ in 0..<30 {
    if let result = find(title) {
      target = result
      break
    }
    Thread.sleep(forTimeInterval: 0.15)
  }
  guard let target else {
    let labels = collect().flatMap { $0.words }
      .filter { $0.contains("Core") || $0.contains("fictional") }
      .prefix(12)
    refuse("cannot reach named control \(title); accessible labels=\(Array(labels))")
  }
  guard AXUIElementPerformAction(target.node, kAXPressAction as CFString) == .success else {
    refuse("native AXPress refused on \(title)")
  }
  // AccessKit updates selection state on the next eframe repaint.
  // A short bounded settle delay avoids racing the follow-up AXPress.
  Thread.sleep(forTimeInterval: 0.4)
}
func assertReceipt(_ expectedHash: String, _ caseName: String) {
  for _ in 0..<30 {
    let words = collect().flatMap { $0.words }
    if words.contains(where: { $0.contains("Source report SHA-256: " + expectedHash) }) &&
       words.contains(where: { $0.contains("Core status: not_validated") }) &&
       words.contains(where: { $0.contains("FHIR R4 NOT validated") })
    {
      print("MACOS_CORE_PROVENANCE_AX_SOURCE_REPORT_PASS " + caseName)
      return
    }
    Thread.sleep(forTimeInterval: 0.16)
  }
  let visible = collect().flatMap { $0.words }.filter {
    $0.contains("Core case:") || $0.contains("Source report SHA-256:") ||
      $0.contains("Core status:") || $0.contains("FAIL CLOSED") ||
      $0.contains("FHIR R4 NOT validated") || $0.contains("Unknown fictional")
  }
  refuse("verified source report not displayed or disclosure missing: " + caseName +
    "; current labels=" + String(describing: Array(visible.prefix(12))))
}
press("Core provenance: two fictional reports")
press("Inspect Core synthetic provenance (read-only)")
assertReceipt(
  "165b41acdc416617e8f207366d454ac6a713ecf4c9a5efd740d14a0af882bd08",
  "known"
)
press("Unknown fictional resource")
press("Inspect Core synthetic provenance (read-only)")
assertReceipt(
  "7962d747049185ce33f252d8760e1197942e6f945d22e9f640df27eaeff1129c",
  "negative"
)
print("MACOS_CORE_PROVENANCE_AX_2_OF_2_PASS_SYNTHETIC_ONLY")
