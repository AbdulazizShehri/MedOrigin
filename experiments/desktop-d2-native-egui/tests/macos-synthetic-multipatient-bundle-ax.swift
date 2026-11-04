import ApplicationServices
import Foundation

// Real Apple Accessibility interaction, exact reviewed dummy-only FHIR-shaped Bundle.
// Does not inspect patient data or use Mac Keychain, files or networking.
func noGo(_ reason: String) -> Never {
  fputs("MACOS_MULTI_PATIENT_BUNDLE_AX_NO_GO: \(reason)\n", stderr)
  exit(1)
}
guard CommandLine.arguments.count == 2,
      let pid = Int32(CommandLine.arguments[1]), pid > 0 else {
  noGo("one exact native GUI pid required")
}
guard AXIsProcessTrusted() else { noGo("native accessibility entitlement absent") }
let app = AXUIElementCreateApplication(pid)
var window: AXUIElement?
for _ in 0..<50 {
  var value: CFTypeRef?
  if AXUIElementCopyAttributeValue(app, kAXWindowsAttribute as CFString, &value) == .success,
     let windows = value as? [AXUIElement], windows.count == 1 {
    window = windows[0]
    break
  }
  Thread.sleep(forTimeInterval: 0.18)
}
guard let nativeWindow = window else { noGo("one native app window required") }

func property(_ item: AXUIElement, _ key: CFString) -> String {
  var value: CFTypeRef?
  if AXUIElementCopyAttributeValue(item, key, &value) != .success { return "" }
  return value as? String ?? ""
}
struct Node {
  let element: AXUIElement
  let role: String
  let labels: [String]
}
func nodes() -> [Node] {
  var result: [Node] = []
  func walk(_ item: AXUIElement, _ depth: Int) {
    if depth > 24 || result.count >= 850 { return }
    result.append(Node(
      element: item,
      role: property(item, kAXRoleAttribute as CFString),
      labels: [
        property(item, kAXTitleAttribute as CFString),
        property(item, kAXDescriptionAttribute as CFString),
        property(item, kAXValueAttribute as CFString)
      ]
    ))
    var children: CFTypeRef?
    if AXUIElementCopyAttributeValue(item, kAXChildrenAttribute as CFString, &children)
      == .success, let items = children as? [AXUIElement] {
      for child in items { walk(child, depth + 1) }
    }
  }
  walk(nativeWindow, 0)
  return result
}
func present(_ wanted: String) -> Bool {
  nodes().contains { $0.labels.contains(where: { $0.contains(wanted) }) }
}
func expect(_ wanted: String) {
  for _ in 0..<45 {
    if present(wanted) { return }
    Thread.sleep(forTimeInterval: 0.12)
  }
  noGo("expected source-only native AX detail absent: " + wanted)
}
func press(_ wanted: String) {
  for _ in 0..<45 {
    let matches = nodes().filter {
      ($0.role == (kAXButtonRole as String) ||
       $0.role == (kAXCheckBoxRole as String)) &&
       $0.labels.contains(where: { $0 == wanted })
    }
    if matches.count == 1 {
      if AXUIElementPerformAction(matches[0].element, kAXPressAction as CFString)
        != .success { noGo("native AX button press refused: " + wanted) }
      Thread.sleep(forTimeInterval: 0.3)
      return
    }
    if matches.count > 1 { noGo("ambiguous AX button: " + wanted) }
    Thread.sleep(forTimeInterval: 0.12)
  }
  noGo("native AX button missing: " + wanted)
}

expect("Fictional Multi-Patient Workspace")
expect("8 imaginary source-only records across 2 fictional patients")
expect("Bundle: 4 of 8 fictional resources visible")
expect("Bundle record: Patient/fictional-patient-001")
press("Bundle: Incoming Encounter/fictional-encounter-001 via subject")
expect("Bundle record: Encounter/fictional-encounter-001")
press("Bundle: Follow subject to Patient/fictional-patient-001")
expect("Bundle record: Patient/fictional-patient-001")
expect("Bundle: 2 of 24 navigation steps")
press("Bundle: Back to previous resource")
expect("Bundle record: Encounter/fictional-encounter-001")
press("Bundle: Back to previous resource")
expect("Bundle record: Patient/fictional-patient-001")

press("Bundle: Patient fictional-patient-002")
expect("Bundle: 4 of 8 fictional resources visible")
press("Bundle: Type Observation")
expect("Bundle: 2 of 8 fictional resources visible")
if present("Bundle: Open Observation/fictional-observation-001") {
  noGo("second fictional patient leaked first patient Observation")
}
press("Bundle: Open Observation/fictional-observation-003")
expect("Bundle record: Observation/fictional-observation-003")
press("Bundle: Follow encounter to Encounter/fictional-encounter-002")
expect("Bundle record: Encounter/fictional-encounter-002")
press("Bundle: Back to previous resource")
expect("Bundle record: Observation/fictional-observation-003")
press("Bundle: All patients")
expect("Bundle: 8 of 8 fictional resources visible")
press("Bundle: Type Patient")
expect("Bundle: 2 of 8 fictional resources visible")
press("Bundle: Clear fictional records")
expect("Native Rust Experiment")
if present("Bundle record: Observation/fictional-observation-003") {
  noGo("cleared fictional source remained accessible")
}
print("MACOS_NATIVE_EIGHT_RECORD_TWO_PATIENT_STRUCTURAL_FHIR_BUNDLE_GROUP_GRAPH_AX_PASS_NONCLINICAL")
