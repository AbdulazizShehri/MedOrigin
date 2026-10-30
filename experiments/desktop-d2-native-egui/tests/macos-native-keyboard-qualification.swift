import AppKit
import ApplicationServices
import Foundation

// Real keyboard-only regression on an authorized Mac running fictional D2.
// Never changes system accessibility settings or touches real patient data.
func fail(_ message: String) -> Never {
  fputs("MACOS_KEYBOARD_NO_GO: \(message)\n", stderr)
  exit(1)
}
guard CommandLine.arguments.count == 2, let pid = Int32(CommandLine.arguments[1]), pid > 0 else {
  fail("expected active synthetic D2 process PID")
}
guard AXIsProcessTrusted() else { fail("accessibility inspection permission missing") }
guard let running = NSRunningApplication(processIdentifier: pid) else {
  fail("synthetic D2 app absent")
}
guard running.activate() else { fail("could not foreground native app") }
let app = AXUIElementCreateApplication(pid)
var windowsValue: CFTypeRef?
guard
  AXUIElementCopyAttributeValue(app, kAXWindowsAttribute as CFString, &windowsValue) == .success,
  let windows = windowsValue as? [AXUIElement], windows.count == 1
else { fail("expected one native window") }
let window = windows[0]
func attribute(_ node: AXUIElement, _ key: CFString) -> String {
  var value: CFTypeRef?
  guard AXUIElementCopyAttributeValue(node, key, &value) == .success else { return "" }
  return String(describing: value ?? "" as CFTypeRef)
}
func texts() -> [String] {
  var out = [String]()
  var count = 0
  func walk(_ node: AXUIElement, _ depth: Int) {
    guard depth < 20 && count < 200 else { return }
    count += 1
    out.append(attribute(node, kAXTitleAttribute as CFString))
    out.append(attribute(node, kAXValueAttribute as CFString))
    var childrenValue: CFTypeRef?
    if AXUIElementCopyAttributeValue(node, kAXChildrenAttribute as CFString, &childrenValue)
      == .success, let children = childrenValue as? [AXUIElement]
    {
      for child in children { walk(child, depth + 1) }
    }
  }
  walk(window, 0)
  return out
}
func focused() -> (role: String, title: String, value: String)? {
  var result: CFTypeRef?
  guard
    AXUIElementCopyAttributeValue(app, kAXFocusedUIElementAttribute as CFString, &result)
      == .success, let result, CFGetTypeID(result) == AXUIElementGetTypeID()
  else { return nil }
  let element = result as! AXUIElement
  return (
    attribute(element, kAXRoleAttribute as CFString),
    attribute(element, kAXTitleAttribute as CFString),
    attribute(element, kAXValueAttribute as CFString)
  )
}
func key(_ code: CGKeyCode, shift: Bool = false) {
  let source = CGEventSource(stateID: .hidSystemState)
  guard let down = CGEvent(keyboardEventSource: source, virtualKey: code, keyDown: true),
    let up = CGEvent(keyboardEventSource: source, virtualKey: code, keyDown: false)
  else { fail("cannot synthesize keyboard input") }
  down.flags = shift ? .maskShift : []
  up.flags = []
  down.post(tap: .cghidEventTap)
  up.post(tap: .cghidEventTap)
  Thread.sleep(forTimeInterval: 0.18)
}
func tab(_ reverse: Bool = false) { key(48, shift: reverse) }
func space() { key(49) }
let fixtures = [
  ("patient-minimal", "747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0"),
  ("patient-invalid-utf8", "a8100ae6aa1940d0b663bb31cd466142ebbdbd5187131b92d93818987832eb89"),
  ("patient-over-limit", "b929f15ca4f3fa28f54991ed0cb8ac5f430e388ee08bf401a853d8af91e44538"),
  ("patient-exact-limit", "ea711ce560191a81c0722c4a26592e0e2d9abb2186b6fd3af6897cd89d417d4e"),
]
let expected = fixtures.map { $0.0 } + ["Verify synthetic SHA-256"]
// First native AX query may return AccessKit's async placeholder tree.
var ready = false
for _ in 0..<20 {
  let visible = texts()
  if expected.allSatisfy({ label in visible.contains(where: { $0.contains(label) }) }) {
    ready = true
    break
  }
  Thread.sleep(forTimeInterval: 0.2)
}
guard ready else { fail("native controls absent after AccessKit activation") }
// Starting focus is not assumed; test must navigate via keyboard only.
var firstReached = false
for _ in 0..<10 {
  if focused()?.title.hasPrefix("patient-minimal (") == true {
    firstReached = true
    break
  }
  tab()
}
guard firstReached else { fail("Tab cannot focus the first fictional selector") }
for (index, name) in expected.enumerated() {
  if index != 0 { tab() }
  guard focused()?.title.hasPrefix(name) == true else {
    fail(
      "forward Tab traversal lost control \(index): expected \(name), got \(focused()?.title ?? "<nil>")"
    )
  }
}
for index in stride(from: expected.count - 2, through: 0, by: -1) {
  tab(true)
  guard focused()?.title.hasPrefix(expected[index]) == true else {
    fail("reverse Shift+Tab focus order differs at \(index)")
  }
}
print("MACOS_KEYBOARD_FOCUS_FORWARD_REVERSE_PASS")
// The action is sent as a genuine Space key, NOT AXPress or a direct Rust hash call.
for (id, digest) in fixtures {
  var found = false
  for _ in 0..<7 {
    if focused()?.title.hasPrefix(id + " (") == true {
      found = true
      break
    }
    tab()
  }
  guard found else { fail("Tab cannot reach selector \(id)") }
  space()
  for _ in 0..<7 {
    if focused()?.title == "Verify synthetic SHA-256" { break }
    tab()
  }
  guard focused()?.title == "Verify synthetic SHA-256" else {
    fail("Tab cannot reach Verify after \(id)")
  }
  space()
  var displayed = false
  for _ in 0..<20 {
    if texts().contains(where: { $0.contains(digest) }) {
      displayed = true
      break
    }
    Thread.sleep(forTimeInterval: 0.2)
  }
  guard displayed else { fail("Space-activated \(id) result missing from AX tree") }
  print("MACOS_KEYBOARD_FIXTURE_PASS \(id)")
}
print("MACOS_KEYBOARD_4_OF_4_PASS_NONPUBLISHING")
