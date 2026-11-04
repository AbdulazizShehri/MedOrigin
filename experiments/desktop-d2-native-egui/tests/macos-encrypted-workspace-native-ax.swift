import ApplicationServices
import Foundation

// Actual macOS AX acceptance of the native synthetic encrypted Workspace
// receipt, from an independently source-verified ephemeral Core demo.
func noGo(_ reason: String) -> Never {
  fputs("MACOS_ENCRYPTED_SYNTHETIC_WORKSPACE_GUI_NO_GO: \(reason)\n", stderr)
  exit(1)
}
guard CommandLine.arguments.count == 3,
      let pid = Int32(CommandLine.arguments[1]), pid > 0 else {
  noGo("exact native GUI PID and pinned summary SHA required")
}
let sha = CommandLine.arguments[2]
guard sha == "25acdb57db8ca3f11d353cf311167973760caaa95bb64de7339fe21e3b05cc2e" else {
  noGo("not the source-reviewed encrypted demo summary SHA")
}
guard AXIsProcessTrusted() else { noGo("macOS Accessibility permission missing") }
let process = AXUIElementCreateApplication(pid)
var window: AXUIElement?
for _ in 0..<40 {
  var result: CFTypeRef?
  if AXUIElementCopyAttributeValue(process, kAXWindowsAttribute as CFString, &result)
     == .success, let windows = result as? [AXUIElement], windows.count == 1 {
    window = windows[0]
    break
  }
  Thread.sleep(forTimeInterval: 0.2)
}
guard let window else { noGo("expected exactly one native window") }

func labels() -> [String] {
  var words = [String]()
  func walk(_ item: AXUIElement, depth: Int) {
    if depth > 22 || words.count >= 850 { return }
    for attribute in [kAXTitleAttribute, kAXDescriptionAttribute, kAXValueAttribute] {
      var value: CFTypeRef?
      if AXUIElementCopyAttributeValue(item, attribute as CFString, &value) == .success,
         let value = value as? String, !value.isEmpty {
        words.append(value)
      }
    }
    var children: CFTypeRef?
    if AXUIElementCopyAttributeValue(item, kAXChildrenAttribute as CFString, &children) == .success,
       let children = children as? [AXUIElement] {
      for child in children { walk(child, depth: depth + 1) }
    }
  }
  walk(window, depth: 0)
  return words
}
let required = [
  "Workspace demo SHA-256: " + sha,
  "Fictional resources: 3",
  "Fictional provenance records: 3",
  "Audit events: 1",
  "Verified encrypted reopen: true",
  "Temporary encrypted store removed: true",
  "Synthetic encrypted ephemeral Workspace QA only",
  "source and freshness NOT authenticated by GUI"
]
for _ in 0..<45 {
  let current = labels()
  if required.allSatisfy({ needle in current.contains(where: { $0.contains(needle) }) }) {
    print("MACOS_INSTALLED_ENCRYPTED_CORE_WORKSPACE_NATIVE_GUI_AX_PASS " + sha)
    exit(0)
  }
  Thread.sleep(forTimeInterval: 0.15)
}
noGo("native GUI refused or did not expose exact source workspace counters and warnings")
