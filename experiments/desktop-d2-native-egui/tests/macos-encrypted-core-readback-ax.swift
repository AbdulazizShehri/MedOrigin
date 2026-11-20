import ApplicationServices
import Foundation

// Real macOS AX interactions with source-verified fictional workspace ONLY.
// No PHI, filesystem import, clinical validity, or product release.
func noGo(_ reason: String) -> Never {
  fputs("MACOS_FICTIONAL_WORKSPACE_AX_NO_GO: \(reason)\n", stderr)
  exit(1)
}
guard (CommandLine.arguments.count == 2 ||
       (CommandLine.arguments.count == 3 &&
        CommandLine.arguments[2] == "--focused-startup")),
      let pid = Int32(CommandLine.arguments[1]), pid > 0 else {
  noGo("exact native D2 PID and optional reviewed focused startup mode required")
}
let focusedStartup = CommandLine.arguments.count == 3
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
func eventuallyText(_ target: String) -> Bool {
  for _ in 0..<32 {
    if textPresent(target) { return true }
    Thread.sleep(forTimeInterval: 0.12)
  }
  return false
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
if focusedStartup {
  guard eventuallyText("MedOrigin focused Workspace"),
        eventuallyText("Source-verified resource browser"),
        eventuallyText("Focus: 3 of 3 source-verified fictional resources visible")
  else { noGo("focused one-shot Core mode did not open Workspace FIRST") }
  if textPresent("Workspace home: fictional Core source only") {
    noGo("focused native start incorrectly exposed developer evidence first")
  }
  press("Focus: Return to developer evidence")
  guard eventuallyText("Workspace home: fictional Core source only")
  else { noGo("focused startup cannot return to original D2 developer evidence") }
  print("MACOS_NATIVE_FOCUSED_SOURCE_STARTUP_FIRST_AX_PASS_NONCLINICAL")
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
press("Open focused fictional Workspace")
guard eventuallyText("MedOrigin focused Workspace"),
      textPresent("3 fictional identities | encrypted reopen: true | audit: true"),
      textPresent("Source: Ephemeral encrypted QA test vault, removed after readback")
else { noGo("focused native fictional Workspace home missing") }
guard eventuallyText("Source-verified resource browser"),
      eventuallyText("Focus: 3 of 3 source-verified fictional resources visible")
else { noGo("focused verified resource browser missing") }
press("Focus: Type Patient")
guard eventuallyText("Focus: 1 of 3 source-verified fictional resources visible")
else { noGo("focused type facet did not narrow to Patient") }
if textPresent("Focus: Inspect Observation/fictional-observation-001") {
  noGo("focused Patient type facet leaked Observation row")
}
press("Focus: Find Encounter")
guard eventuallyText("Focus: 0 of 3 source-verified fictional resources visible"),
      eventuallyText("No fictional resources match the chosen type and identity keyword.")
else { noGo("focused type and identity keyword did not compose") }
press("Focus: Type Encounter")
guard eventuallyText("Focus: 1 of 3 source-verified fictional resources visible")
else { noGo("focused Encounter facet did not restore one result") }
press("Focus: Inspect Encounter/fictional-encounter-001")
guard eventuallyText("Focused fictional record: Encounter/fictional-encounter-001")
else { noGo("focused selected visible Encounter source row did not open") }
press("Focus: Find All")
press("Focus: Type All")
guard eventuallyText("Focus: 3 of 3 source-verified fictional resources visible")
else { noGo("focused filters did not restore full verified Core worklist") }
press("Focus: Find Observation")
guard eventuallyText("Focus: 1 of 3 source-verified fictional resources visible")
else { noGo("focused Observation search did not narrow source worklist") }
press("Focus: Inspect Observation/fictional-observation-001")
guard eventuallyText("Focused fictional record: Observation/fictional-observation-001")
else { noGo("focused filtered source Observation row did not open") }
press("Focus: Find All")
guard eventuallyText("Focus: 3 of 3 source-verified fictional resources visible")
else { noGo("focused keyword clearing did not restore source worklist") }
print("MACOS_NATIVE_FOCUSED_SOURCE_BROWSER_FILTER_SEARCH_OPEN_AX_PASS_NONCLINICAL")
press("Focus: Open Patient")
guard eventuallyText("Focused fictional record: Patient/fictional-patient-001")
else {
  let labels = visibleNodes().flatMap { $0.labels }.filter {
    $0.contains("Focus:") || $0.contains("Focused fictional") ||
    $0.contains("Workspace") || $0.contains("Patient") ||
    $0.contains("Source-verified")
  }.prefix(30)
  noGo("focused patient not source-linked; actual AX labels: " +
       String(describing: Array(labels)))
}
guard eventuallyText("Focus: 0 outgoing and 2 incoming source links")
else { noGo("focused real-source Patient incoming edge count incorrect") }
press("Focus: Open incoming Encounter/fictional-encounter-001 via subject")
guard eventuallyText("Focused fictional record: Encounter/fictional-encounter-001")
else { noGo("focused incoming Encounter.subject not resolved") }
press("Focus: Follow outgoing subject to Patient/fictional-patient-001")
guard eventuallyText("Focused fictional record: Patient/fictional-patient-001"),
      eventuallyText("Focus: Verified navigation trail 2 of 16 steps")
else { noGo("focused outgoing Encounter.subject or trail not verified") }
press("Focus: Jump history 2: Encounter/fictional-encounter-001")
guard eventuallyText("Focused fictional record: Encounter/fictional-encounter-001")
else { noGo("focused verified breadcrumb did not jump to Encounter") }
press("Focus: Back along verified path")
guard eventuallyText("Focused fictional record: Patient/fictional-patient-001")
else { noGo("focused back along source history failed") }
press("Focus: Open incoming Observation/fictional-observation-001 via subject")
guard eventuallyText("Focused fictional record: Observation/fictional-observation-001")
else { noGo("focused Observation.subject reverse edge missing") }
press("Focus: Follow outgoing encounter to Encounter/fictional-encounter-001")
guard eventuallyText("Focused fictional record: Encounter/fictional-encounter-001")
else { noGo("focused Observation.encounter outgoing edge missing") }
press("Focus: Jump history 1: Patient/fictional-patient-001")
guard eventuallyText("Focused fictional record: Patient/fictional-patient-001")
else { noGo("focused verified patient breadcrumb not restored") }
print("MACOS_NATIVE_FOCUSED_WORKSPACE_SOURCE_LINK_GRAPH_AND_HISTORY_AX_PASS_NONCLINICAL")
press("Focus: Open Encounter")
guard eventuallyText("Focused fictional record: Encounter/fictional-encounter-001")
else { noGo("focused Encounter not source-linked") }
press("Focus: Back along verified path")
guard eventuallyText("Focused fictional record: Patient/fictional-patient-001")
else { noGo("focused Back did not return to patient") }
press("Focus: Open Observation")
guard eventuallyText("Focused fictional record: Observation/fictional-observation-001")
else {
  let labels = visibleNodes().flatMap { $0.labels }.filter {
    $0.contains("Focus:") || $0.contains("Focused fictional") ||
    $0.contains("Workspace") || $0.contains("Observation") || $0.contains("Patient")
  }.prefix(24)
  noGo("focused Observation not source-linked; actual visible AX labels: " +
       String(describing: Array(labels)))
}
press("Focus: Mark visited (demo only)")
guard eventuallyText("Fictional walkthrough: 1 of 3 visited this session")
else { noGo("focused visit state did not update") }
press("Focus: Reset visits")
guard eventuallyText("Fictional walkthrough: 0 of 3 visited this session")
else { noGo("focused visit state did not reset") }
press("Focus: Return to developer evidence")
guard eventuallyText("Workspace home: fictional Core source only")
else { noGo("focused view did not return to prior developer UI") }
print("MACOS_NATIVE_FOCUSED_FICTIONAL_WORKSPACE_PATIENT_CONTEXT_AX_PASS_NONCLINICAL")
guard textPresent("Fictional session walkthrough: 0 of 3 identities visited")
else { noGo("fictional session walkthrough did not start empty") }
press("Open next unvisited fictional identity")
guard textPresent("Recovered fictional record: Patient/fictional-patient-001")
else { noGo("walkthrough did not start from fictional Patient") }
press("Mark fictional identity visited (demo only)")
guard textPresent("Fictional session walkthrough: 1 of 3 identities visited")
else { noGo("fictional patient walkthrough not recorded in memory") }
press("Open next unvisited fictional identity")
guard textPresent("Recovered fictional record: Encounter/fictional-encounter-001")
else { noGo("fictional walkthrough next Encounter missing") }
press("Mark fictional identity visited (demo only)")
guard textPresent("Fictional session walkthrough: 2 of 3 identities visited")
else { noGo("fictional encounter walkthrough not recorded in memory") }
press("Open next unvisited fictional identity")
guard textPresent("Recovered fictional record: Observation/fictional-observation-001")
else { noGo("fictional walkthrough next Observation missing") }
press("Mark fictional identity visited (demo only)")
guard textPresent("Fictional session walkthrough: 3 of 3 identities visited")
else { noGo("fictional walkthrough did not complete all three") }
press("Open next unvisited fictional identity")
guard textPresent("All three fictional walkthrough steps complete (session only)")
else { noGo("fictional walkthrough completion notice missing") }
press("Reset fictional walkthrough (session only)")
guard textPresent("Fictional session walkthrough: 0 of 3 identities visited")
else { noGo("fictional walkthrough reset did not clear in-memory progress") }
print("MACOS_NATIVE_FICTIONAL_WALKTHROUGH_3_RESOURCES_AX_PASS_NOT_CLINICAL")
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
guard eventuallyText("Recovered fictional record: Observation/fictional-observation-001")
  else { noGo("recovered encrypted Observation detail not visible") }
press("Follow recovered fictional subject -> urn:uuid:00000000-0000-4000-8000-000000000002")
guard eventuallyText("Recovered fictional record: Patient/fictional-patient-001")
  else { noGo("encrypted source recovered Patient relationship not navigated") }
press("Back to previous recovered fictional record")
guard eventuallyText("Recovered fictional record: Observation/fictional-observation-001")
  else { noGo("Back from decrypted Patient failed") }
press("Follow recovered fictional encounter -> urn:uuid:00000000-0000-4000-8000-000000000003")
guard eventuallyText("Recovered fictional record: Encounter/fictional-encounter-001")
  else { noGo("decrypted Encounter reference not navigated") }
press("Back to previous recovered fictional record")
guard eventuallyText("Recovered fictional record: Observation/fictional-observation-001")
  else { noGo("back from decrypted Encounter failed") }
press("Clear encrypted Core readback display")
for _ in 0..<30 {
  if !textPresent("Recovered fictional record: Observation/fictional-observation-001") {
    break
  }
  Thread.sleep(forTimeInterval: 0.12)
}
if textPresent("Recovered fictional record: Observation/fictional-observation-001") {
  noGo("encrypted Core readback record leaked after clear")
}
print("MACOS_REAL_ENCRYPTED_CORE_READBACK_NATIVE_THREE_FICTIONAL_RESOURCE_NAV_AX_PASS_NOT_CLINICAL")
