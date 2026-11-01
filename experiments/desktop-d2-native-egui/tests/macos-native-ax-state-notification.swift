import AppKit
import ApplicationServices
import Foundation

// Nonpublishing, real-mac semantic and AX notification qualification for fictional D2.
// This does NOT assert VoiceOver speech, audio output or release accessibility approval.
func fail(_ reason: String) -> Never {
  fputs("D2_MAC_AX_SEMANTICS_NO_GO: \(reason)\n", stderr)
  exit(1)
}

guard CommandLine.arguments.count == 2,
  let pid = Int32(CommandLine.arguments[1]), pid > 0,
  AXIsProcessTrusted(),
  NSRunningApplication(processIdentifier: pid) != nil
else {
  fail("expected live synthetic D2 PID with Accessibility permission")
}
let app = AXUIElementCreateApplication(pid)
let fixtures = [
  "patient-minimal", "patient-invalid-utf8", "patient-over-limit", "patient-exact-limit",
]

func attribute(_ node: AXUIElement, _ key: CFString) -> String {
  var value: CFTypeRef?
  guard AXUIElementCopyAttributeValue(node, key, &value) == .success,
    let value
  else { return "" }
  return String(describing: value)
}

func controls() -> ([String: AXUIElement], AXUIElement?) {
  var selectors = [String: AXUIElement]()
  var verify: AXUIElement?
  var visited = 0
  func walk(_ node: AXUIElement, _ depth: Int) {
    guard depth < 20, visited < 300 else { return }
    visited += 1
    let role = attribute(node, kAXRoleAttribute as CFString)
    let title = attribute(node, kAXTitleAttribute as CFString)
    if role == (kAXCheckBoxRole as String) {
      for id in fixtures where title.hasPrefix(id + " (") {
        selectors[id] = node
      }
    }
    if role == (kAXButtonRole as String) && title == "Verify synthetic SHA-256" {
      verify = node
    }
    var value: CFTypeRef?
    if AXUIElementCopyAttributeValue(node, kAXChildrenAttribute as CFString, &value)
      == .success, let children = value as? [AXUIElement]
    {
      for child in children { walk(child, depth + 1) }
    }
  }
  var value: CFTypeRef?
  if AXUIElementCopyAttributeValue(app, kAXWindowsAttribute as CFString, &value)
    == .success, let windows = value as? [AXUIElement], windows.count == 1
  {
    walk(windows[0], 0)
  }
  return (selectors, verify)
}

var selectors = [String: AXUIElement]()
var verify: AXUIElement?
// AccessKit's native tree may initialize asynchronously on first AX request.
for _ in 0..<20 {
  (selectors, verify) = controls()
  if selectors.count == fixtures.count && verify != nil { break }
  Thread.sleep(forTimeInterval: 0.2)
}
guard selectors.count == fixtures.count, let button = verify else {
  fail("missing native AX selector or Verify control")
}
guard attribute(button, kAXEnabledAttribute as CFString) == "1",
  !attribute(button, kAXRoleDescriptionAttribute as CFString).isEmpty
else { fail("Verify control missing enabled state or spoken role description") }
for id in fixtures {
  guard let node = selectors[id],
    attribute(node, kAXEnabledAttribute as CFString) == "1",
    !attribute(node, kAXRoleDescriptionAttribute as CFString).isEmpty,
    ["0", "1"].contains(attribute(node, kAXValueAttribute as CFString))
  else { fail("selector lacks readable enabled/role/selected semantics: \(id)") }
}

var eventCounts = [String: Int]()
var observer: AXObserver?
let observerError = AXObserverCreate(
  pid,
  { _, element, notification, _ in
    guard (notification as String) == (kAXValueChangedNotification as String) else {
      return
    }
    let title = attribute(element, kAXTitleAttribute as CFString)
    for id in fixtures where title.hasPrefix(id + " (") {
      eventCounts[id, default: 0] += 1
    }
  }, &observer)
guard observerError == .success, let observer else {
  fail("cannot observe real native AXValueChanged notifications")
}
for id in fixtures {
  guard let node = selectors[id],
    AXObserverAddNotification(observer, node, kAXValueChangedNotification as CFString, nil)
      == .success
  else { fail("cannot register AXValueChanged on \(id)") }
}
CFRunLoopAddSource(
  CFRunLoopGetCurrent(), AXObserverGetRunLoopSource(observer), CFRunLoopMode.defaultMode)

// Normalize any pre-existing user/test selection to the first fictional fixture.
// This is required when the same app process is reused across test runs.
guard let initial = selectors[fixtures[0]],
  AXUIElementPerformAction(initial, kAXPressAction as CFString) == .success
else { fail("cannot reset fictional selection") }
var reset = false
for _ in 0..<20 {
  CFRunLoopRunInMode(CFRunLoopMode.defaultMode, 0.1, false)
  if attribute(initial, kAXValueAttribute as CFString) == "1" {
    reset = true
    break
  }
}
guard reset else { fail("cannot establish initial selected fixture") }

// Every tested action now changes its selected state from 0 to 1.
for id in [fixtures[1], fixtures[2], fixtures[3], fixtures[0]] {
  guard let node = selectors[id] else { fail("selector disappeared: \(id)") }
  let before = eventCounts[id, default: 0]
  guard AXUIElementPerformAction(node, kAXPressAction as CFString) == .success else {
    fail("native AXPress rejected \(id)")
  }
  var qualified = false
  for _ in 0..<20 {
    CFRunLoopRunInMode(CFRunLoopMode.defaultMode, 0.1, false)
    let actual = fixtures.map {
      attribute(selectors[$0]!, kAXValueAttribute as CFString)
    }
    let expected = fixtures.map { $0 == id ? "1" : "0" }
    if actual == expected && eventCounts[id, default: 0] > before {
      qualified = true
      break
    }
  }
  guard qualified else {
    fail("missing live selected state or AXValueChanged event for \(id)")
  }
  print("D2_MAC_AX_STATE_AND_EVENT_PASS \(id)")
}
print("D2_MAC_AX_4_OF_4_STATE_NOTIFICATIONS_PASS_NOT_VOICEOVER_SPEECH")
