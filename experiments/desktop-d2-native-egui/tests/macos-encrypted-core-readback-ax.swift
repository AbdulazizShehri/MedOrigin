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
let readbackSHA = "c99af04367aeaedeecb29b7fccc8a8fb58f2a85753eeae874eae5ad363307a49"
for required in [
  "Recovered fictional resource count: 3",
  "Encrypted readback SHA-256: " + readbackSHA,
  "Audit chain verified: true",
  "Encrypted store reopened: true",
  "Ephemeral encrypted store removed: true",
  "Sender/freshness NOT authenticated",
  "NOT patient records or clinical validation"
] {
  var present = false
  for _ in 0..<45 {
    if textPresent(required) { present = true; break }
    Thread.sleep(forTimeInterval: 0.12)
  }
  if !present {
    noGo("recovered Core window did not expose reviewed field: " + required)
  }
}
for label in [
  "Workspace home: fictional Core source only",
  "Verified fictional resources: 3 (read-only)",
  "Workspace source: Reopened ephemeral encrypted test vault (removed after QA)"
] {
  guard textPresent(label) else { noGo("native Workspace home absent: " + label) }
}
press("Open workspace home: fictional patient chart")
guard textPresent("Recovered fictional record: Patient/fictional-patient-001"),
      textPresent("Fictional patient chart: source-verified relationships"),
      textPresent("Associated fictional resources: 1 Encounter, 1 Observation")
else { noGo("native fictional patient chart graph not displayed from Workspace home") }
press("Open patient chart member: Encounter/fictional-encounter-001")
guard textPresent("Recovered fictional record: Encounter/fictional-encounter-001")
else { noGo("source-linked fictional Encounter chart navigation failed") }
press("Back to previous recovered fictional record")
guard textPresent("Recovered fictional record: Patient/fictional-patient-001")
else { noGo("Back from fictional Encounter chart to Patient failed") }
press("Open patient chart member: Observation/fictional-observation-001")
guard textPresent("Recovered fictional record: Observation/fictional-observation-001")
else { noGo("source-linked fictional Observation chart navigation failed") }
press("Back to previous recovered fictional record")
guard textPresent("Recovered fictional record: Patient/fictional-patient-001")
else { noGo("Back from fictional Observation chart to Patient failed") }
print("MACOS_NATIVE_WORKSPACE_HOME_PATIENT_CHART_AX_PASS_NONCLINICAL")
press("Open recovered fictional resource: Observation/fictional-observation-001")
guard textPresent("Recovered fictional record: Observation/fictional-observation-001")
  else { noGo("recovered encrypted Observation detail not visible") }
press("Follow recovered fictional subject -> urn:uuid:00000000-0000-4000-8000-000000000002")
guard textPresent("Recovered fictional record: Patient/fictional-patient-001")
  else { noGo("encrypted source recovered Patient relationship not navigated") }
press("Back to previous recovered fictional record")
guard textPresent("Recovered fictional record: Observation/fictional-observation-001")
  else { noGo("Back from decrypted Patient failed") }
press("Follow recovered fictional encounter -> urn:uuid:00000000-0000-4000-8000-000000000003")
guard textPresent("Recovered fictional record: Encounter/fictional-encounter-001")
  else { noGo("decrypted Encounter reference not navigated") }
press("Back to previous recovered fictional record")
guard textPresent("Recovered fictional record: Observation/fictional-observation-001")
  else { noGo("back from decrypted Encounter failed") }
press("Clear encrypted Core readback display")
if textPresent("Recovered fictional record: Observation/fictional-observation-001") {
  noGo("encrypted Core readback record leaked after clear")
}
print("MACOS_REAL_ENCRYPTED_CORE_READBACK_NATIVE_THREE_FICTIONAL_RESOURCE_NAV_AX_PASS_NOT_CLINICAL")
