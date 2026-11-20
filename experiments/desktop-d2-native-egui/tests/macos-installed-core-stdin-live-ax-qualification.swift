import ApplicationServices
import Foundation

// Actual window source-backed external stdin synthetic Core receipt admission.
// Caller has independently checked Core installed-Wheel, sandbox, Python, Rust
// and GUI executable hashes; no external data, PHI or clinical claim.
func noGo(_ reason: String) -> Never {
  fputs("MACOS_INSTALLED_CORE_STDIN_GUI_AX_NO_GO: \(reason)\n", stderr)
  exit(1)
}
guard CommandLine.arguments.count == 3,
      let pid = Int32(CommandLine.arguments[1]), pid > 0 else {
  noGo("native GUI PID and exact source report SHA required")
}
let digest = CommandLine.arguments[2]
guard digest.count == 64,
      digest.utf8.allSatisfy({ $0 >= 48 && $0 <= 57 || $0 >= 97 && $0 <= 102 })
else { noGo("unreviewed expected report hash") }
guard AXIsProcessTrusted() else { noGo("macOS Accessibility permission unavailable") }
let app = AXUIElementCreateApplication(pid)
var window: AXUIElement?
for _ in 0..<40 {
  var attribute: CFTypeRef?
  if AXUIElementCopyAttributeValue(app, kAXWindowsAttribute as CFString, &attribute)
    == .success, let windows = attribute as? [AXUIElement], windows.count == 1 {
    window = windows[0]
    break
  }
  Thread.sleep(forTimeInterval: 0.2)
}
guard let window else { noGo("exactly one native GUI window not observed") }

func attribute(_ node: AXUIElement, _ key: CFString) -> String {
  var value: CFTypeRef?
  if AXUIElementCopyAttributeValue(node, key, &value) != .success { return "" }
  return value as? String ?? ""
}
func labels() -> [String] {
  var words = [String]()
  func scan(_ node: AXUIElement, _ depth: Int) {
    if depth > 22 || words.count > 950 { return }
    for key in [kAXTitleAttribute, kAXDescriptionAttribute, kAXValueAttribute] {
      let text = attribute(node, key as CFString)
      if !text.isEmpty { words.append(text) }
    }
    var children: CFTypeRef?
    if AXUIElementCopyAttributeValue(node, kAXChildrenAttribute as CFString, &children)
      == .success, let items = children as? [AXUIElement] {
      for item in items { scan(item, depth + 1) }
    }
  }
  scan(window, 0)
  return words
}
for _ in 0..<40 {
  let all = labels()
  let source = all.contains { $0.contains("Source report SHA-256: " + digest) }
  let status = all.contains { $0.contains("Core status: not_validated") }
  let clinical = all.contains { $0.contains("FHIR R4 NOT validated") }
  let external = all.contains {
    $0.contains("One-shot external stdin synthetic Core report accepted")
  }
  if source && status && clinical && external {
    print("MACOS_INSTALLED_CORE_STDIN_GUI_AX_EXACT_SHA_NOT_VALIDATED_PASS " + digest)
    exit(0)
  }
  Thread.sleep(forTimeInterval: 0.17)
}
noGo("native GUI missing exact SHA/status/clinical warning/external-origin disclosure")
