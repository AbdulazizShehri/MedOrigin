import ApplicationServices
import Foundation

// Real macOS NSAccessibility qualification. Runs only on an authorized Mac;
// accepts a disposable synthetic-only native D2 app PID, not clinical data.
guard CommandLine.arguments.count == 2, let pid = Int32(CommandLine.arguments[1]), pid > 0 else {
  fputs("usage: swift macos-native-ax-qualification.swift <synthetic-preview-PID>\n", stderr)
  exit(2)
}
guard AXIsProcessTrusted() else {
  fputs("MACOS_AX_NO_GO: accessibility permission missing (cannot qualify)\n", stderr)
  exit(1)
}
let app = AXUIElementCreateApplication(pid)
var windowsValue: CFTypeRef?
guard
  AXUIElementCopyAttributeValue(app, kAXWindowsAttribute as CFString, &windowsValue) == .success,
  let windows = windowsValue as? [AXUIElement], windows.count == 1
else {
  fputs("MACOS_AX_NO_GO: expected exactly one accessible preview window\n", stderr)
  exit(1)
}
func stringValue(_ element: AXUIElement, _ attribute: CFString) -> String {
  var value: CFTypeRef?
  guard AXUIElementCopyAttributeValue(element, attribute, &value) == .success else { return "" }
  return value as? String ?? ""
}
var words = [String]()
var verifyButton: AXUIElement?
var selectors = [String: AXUIElement]()
var count = 0
func visit(_ node: AXUIElement, _ depth: Int) {
  guard depth <= 18, count < 800 else { return }
  count += 1
  let role = stringValue(node, kAXRoleAttribute as CFString)
  let labels = [
    stringValue(node, kAXTitleAttribute as CFString),
    stringValue(node, kAXDescriptionAttribute as CFString),
    stringValue(node, kAXValueAttribute as CFString),
    stringValue(node, kAXHelpAttribute as CFString),
  ]
  words.append(contentsOf: labels)
  if role == (kAXButtonRole as String)
    && labels.contains(where: { $0.contains("Verify synthetic SHA-256") })
  {
    verifyButton = node
  }
  if role == (kAXCheckBoxRole as String) {
    for id in [
      "patient-minimal", "patient-invalid-utf8", "patient-over-limit", "patient-exact-limit",
    ] {
      if labels.contains(where: { $0.contains(id + " (") }) {
        selectors[id] = node
      }
    }
  }
  var childrenValue: CFTypeRef?
  if AXUIElementCopyAttributeValue(node, kAXChildrenAttribute as CFString, &childrenValue)
    == .success,
    let children = childrenValue as? [AXUIElement]
  {
    for child in children { visit(child, depth + 1) }
  }
}
func collect() {
  words.removeAll()
  count = 0
  verifyButton = nil
  selectors.removeAll()
  visit(windows[0], 0)
}
let required = [
  "patient-minimal", "patient-invalid-utf8", "patient-over-limit",
  "patient-exact-limit", "Verify synthetic SHA-256",
]
// AccessKit may return a placeholder AX tree on the first native request.
// Re-query the live window until asynchronous initialization completes.
var missing = required
for _ in 0..<20 {
  collect()
  missing = required.filter { name in !words.contains(where: { $0.contains(name) }) }
  if missing.isEmpty && verifyButton != nil { break }
  Thread.sleep(forTimeInterval: 0.2)
}
guard missing.isEmpty, verifyButton != nil else {
  fputs(
    "MACOS_AX_NO_GO: node_count=\(count), missing=\(missing.joined(separator: ",")); native controls not exposed\n",
    stderr)
  exit(1)
}
let fixtures = [
  ("patient-minimal", "747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0"),
  ("patient-invalid-utf8", "a8100ae6aa1940d0b663bb31cd466142ebbdbd5187131b92d93818987832eb89"),
  ("patient-over-limit", "b929f15ca4f3fa28f54991ed0cb8ac5f430e388ee08bf401a853d8af91e44538"),
  ("patient-exact-limit", "ea711ce560191a81c0722c4a26592e0e2d9abb2186b6fd3af6897cd89d417d4e"),
]
for (id, digest) in fixtures {
  collect()
  guard let selector = selectors[id],
    AXUIElementPerformAction(selector, kAXPressAction as CFString) == .success
  else {
    fputs("MACOS_AX_NO_GO: cannot select fixture \(id) via NSAccessibility\n", stderr)
    exit(1)
  }
  Thread.sleep(forTimeInterval: 0.3)
  collect()
  guard let button = verifyButton,
    AXUIElementPerformAction(button, kAXPressAction as CFString) == .success
  else {
    fputs("MACOS_AX_NO_GO: cannot invoke native Verify action for \(id)\n", stderr)
    exit(1)
  }
  var resultVisible = false
  for _ in 0..<20 {
    Thread.sleep(forTimeInterval: 0.2)
    collect()
    if words.contains(where: { $0.contains(digest) }) {
      resultVisible = true
      break
    }
  }
  guard resultVisible else {
    fputs("MACOS_AX_NO_GO: selected \(id), but SHA-256 result not readable from AX\n", stderr)
    exit(1)
  }
  print("MACOS_AX_FIXTURE_PASS \(id)")
}
print("MACOS_AX_NATIVE_UIA_4_OF_4_PASS_NONPUBLISHING node_count=\(count)")
