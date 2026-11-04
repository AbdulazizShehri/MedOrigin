import ApplicationServices
import Foundation

// Real macOS AX interactions with source-verified fictional workspace ONLY.
// No PHI, filesystem import, clinical validity, or product release.
func noGo(_ reason: String) -> Never {
  fputs("MACOS_FICTIONAL_WORKSPACE_AX_NO_GO: \(reason)\n", stderr)
  exit(1)
}
guard CommandLine.arguments.count == 2,
      let pid = Int32(CommandLine.arguments[1]), pid > 0 else {
  noGo("exact signed native D2 PID required")
}
guard AXIsProcessTrusted() else { noGo("explicit accessibility permission absent") }
let app = AXUIElementCreateApplication(pid)
var nativeWindow: AXUIElement?
for _ in 0..<40 {
  var windowValue: CFTypeRef?
  if AXUIElementCopyAttributeValue(app, kAXWindowsAttribute as CFString, &windowValue)
    == .success, let windows = windowValue as? [AXUIElement], windows.count == 1 {
    nativeWindow = windows[0]
    break
  }
  Thread.sleep(forTimeInterval: 0.2)
}
guard let window = nativeWindow else { noGo("expected exactly one AX window") }

func property(_ item: AXUIElement, _ attr: CFString) -> String {
  var value: CFTypeRef?
  if AXUIElementCopyAttributeValue(item, attr, &value) != .success { return "" }
  return value as? String ?? ""
}
struct Node {
  let element: AXUIElement
  let role: String
  let labels: [String]
}
func visibleNodes() -> [Node] {
  var nodes = [Node]()
  func walk(_ elem: AXUIElement, _ depth: Int) {
    if depth > 22 || nodes.count >= 750 { return }
    nodes.append(Node(
      element: elem,
      role: property(elem, kAXRoleAttribute as CFString),
      labels: [
        property(elem, kAXTitleAttribute as CFString),
        property(elem, kAXDescriptionAttribute as CFString),
        property(elem, kAXValueAttribute as CFString)
      ]
    ))
    var children: CFTypeRef?
    if AXUIElementCopyAttributeValue(elem, kAXChildrenAttribute as CFString, &children)
      == .success, let items = children as? [AXUIElement] {
      for child in items { walk(child, depth + 1) }
    }
  }
  walk(window, 0)
  return nodes
}
func textPresent(_ text: String) -> Bool {
  visibleNodes().contains { $0.labels.contains(where: { $0.contains(text) }) }
}
func press(_ title: String) {
  for _ in 0..<35 {
    let found = visibleNodes().filter {
      ($0.role == (kAXButtonRole as String) ||
       $0.role == (kAXCheckBoxRole as String)) &&
       $0.labels.contains(where: { $0.contains(title) })
    }
    if found.count == 1 {
      guard AXUIElementPerformAction(found[0].element, kAXPressAction as CFString)
        == .success else { noGo("AXPress refused: " + title) }
      Thread.sleep(forTimeInterval: 0.35)
      return
    }
    if found.count > 1 { noGo("ambiguous actionable control " + title) }
    Thread.sleep(forTimeInterval: 0.16)
  }
  let names = visibleNodes().flatMap { $0.labels }.filter {
    $0.contains("fictional") || $0.contains("case") || $0.contains("Workspace")
  }.prefix(10)
  noGo("missing actionable control " + title + "; seen=" + String(describing: Array(names)))
}
func detail(_ name: String, _ sha: String, _ status: String, _ relation: String?) {
  for _ in 0..<35 {
    if textPresent("Fictional case: " + name)
      && textPresent("Source SHA-256: " + sha)
      && textPresent("Expected developer envelope status: " + status)
      && textPresent("Clinical data: PROHIBITED") {
      if relation == nil || textPresent(relation!) {
        print("MACOS_FICTIONAL_WORKSPACE_AX_CASE_PASS " + name)
        return
      }
    }
    Thread.sleep(forTimeInterval: 0.15)
  }
  noGo("actual native workspace detail missing/invalid for " + name)
}
press("Fictional Workspace — six source-verified cases")
press("Enter fictional workspace (synthetic only)")
press("Open fictional case: observation-minimal")
detail("observation-minimal",
  "527806e5427cc45e55424d1b8dc8ddcdc86a2b37df2ae116735e6832268b5e19",
  "FHIR_ENVELOPE_OK", "/subject/reference")
press("Expected-negative developer controls")
if textPresent("Fictional case: observation-minimal") {
  noGo("old positive detail leaked after negative filter")
}
press("Open fictional case: observation-bad-subject")
detail("observation-bad-subject",
  "d2332ed753a59b46d19a11849cccd96a4250120ad3eab455580ce45b1d91b838",
  "INVALID_REFERENCE", nil)
press("Open fictional case: bundle-dangling")
detail("bundle-dangling",
  "1bbc0bac94b3ff19dce3502164f3243748cf5aa7e869433bdb09e7ec2266b229",
  "INVALID_REFERENCE", nil)
press("Expected-positive developer controls")
if textPresent("Fictional case: bundle-dangling") {
  noGo("old negative detail leaked after positive filter")
}
press("Open fictional case: bundle-linked")
detail("bundle-linked",
  "1d24976b74ab0481ce2acc1010d58ec5e4b9da9ba93071e1042afeb299a03d88",
  "BUNDLE_GRAPH_OK", "/entry/1/resource/subject/reference")
press("Close fictional workspace and clear details")
if textPresent("Fictional case: bundle-linked") {
  noGo("source details remained after explicit workspace close")
}
if !textPresent("Enter fictional workspace (synthetic only)") {
  noGo("workspace not closed, synthetic intent gate missing")
}
print("MACOS_FICTIONAL_WORKSPACE_AX_4_CASES_FILTER_AND_CLEAR_PASS_NOT_CLINICAL")
