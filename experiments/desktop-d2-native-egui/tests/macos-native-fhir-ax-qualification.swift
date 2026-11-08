import AppKit
import ApplicationServices
import CryptoKit
import Foundation

// Actual macOS NSAccessibility acceptance for the eight fictional D2
// Observation/Bundle cases. No VoiceOver spoken-output claim or network proof.
func refuse(_ why: String) -> Never {
  fputs("MACOS_D2_FHIR_AX_NO_GO: \(why)\n", stderr)
  exit(1)
}

guard CommandLine.arguments.count == 3,
  let pid = Int32(CommandLine.arguments[1]), pid > 0
else { refuse("expected native D2 PID and externally approved executable SHA-256") }
let expectedSha = CommandLine.arguments[2].lowercased()
guard expectedSha.count == 64,
  expectedSha.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) })
else { refuse("expected SHA-256 must be 64 ASCII hex digits") }
guard let running = NSRunningApplication(processIdentifier: pid),
  let executable = running.executableURL,
  executable.lastPathComponent == "medorigin-desktop-d2-native-egui",
  let bytes = try? Data(contentsOf: executable)
else { refuse("running native executable identity not accessible") }
let actualSha = SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
guard actualSha == expectedSha else { refuse("running native binary SHA-256 mismatch") }
guard AXIsProcessTrusted() else { refuse("AXIsProcessTrusted() is false") }

let app = AXUIElementCreateApplication(pid)
var windowsValue: CFTypeRef?
guard
  AXUIElementCopyAttributeValue(app, kAXWindowsAttribute as CFString, &windowsValue) == .success,
  let windows = windowsValue as? [AXUIElement], windows.count == 1
else { refuse("expected one authorized native preview window") }
let window = windows[0]
struct Node {
  let element: AXUIElement
  let role: String
  let labels: [String]
}
func text(_ element: AXUIElement, _ key: CFString) -> String {
  var value: CFTypeRef?
  guard AXUIElementCopyAttributeValue(element, key, &value) == .success else { return "" }
  return value as? String ?? ""
}
func nodes() -> [Node] {
  var result: [Node] = []
  func visit(_ element: AXUIElement, _ depth: Int) {
    guard depth <= 24, result.count < 1000 else { return }
    result.append(
      Node(
        element: element,
        role: text(element, kAXRoleAttribute as CFString),
        labels: [
          text(element, kAXTitleAttribute as CFString),
          text(element, kAXDescriptionAttribute as CFString),
          text(element, kAXValueAttribute as CFString),
          text(element, kAXHelpAttribute as CFString),
        ]
      ))
    var childrenValue: CFTypeRef?
    if AXUIElementCopyAttributeValue(element, kAXChildrenAttribute as CFString, &childrenValue)
      == .success, let children = childrenValue as? [AXUIElement]
    {
      for child in children { visit(child, depth + 1) }
    }
  }
  visit(window, 0)
  return result
}
func matched(_ current: [Node], _ role: String? = nil, _ fragment: String) -> [Node] {
  current.filter { node in
    (role == nil || node.role == role)
      && node.labels.contains(where: { $0.contains(fragment) })
  }
}
func perform(_ node: Node, _ label: String) {
  guard AXUIElementPerformAction(node.element, kAXPressAction as CFString) == .success
  else { refuse("AXPress unsupported for \(label), role=\(node.role)") }
}
let headerTitle = "Additional fictional FHIR/Bundle cases (8)"
var header: Node?
for _ in 0..<30 {
  let current = nodes()
  let found = matched(current, nil, headerTitle)
  let actionable = found.filter {
    $0.role == (kAXButtonRole as String) || $0.role == "AXDisclosureTriangle"
      || $0.role == (kAXCheckBoxRole as String)
  }
  if actionable.count == 1 {
    header = actionable[0]
    break
  }
  Thread.sleep(forTimeInterval: 0.2)
}
guard let header else {
  let titles = matched(nodes(), nil, "Additional fictional FHIR/Bundle").map {
    "\($0.role):\($0.labels.joined(separator: "|"))"
  }
  refuse("collapsible AX control missing or ambiguous \(titles)")
}
perform(header, headerTitle)
let cases: [(id: String, sha: String, status: String, bytes: Int)] = [
  (
    "observation-minimal", "527806e5427cc45e55424d1b8dc8ddcdc86a2b37df2ae116735e6832268b5e19",
    "FHIR_ENVELOPE_OK", 251
  ),
  (
    "observation-bad-subject", "d2332ed753a59b46d19a11849cccd96a4250120ad3eab455580ce45b1d91b838",
    "INVALID_REFERENCE", 253
  ),
  (
    "bundle-valid", "3a530a66c0f2b71908b1282985432e405f0f2f412c7ccc0143aa1972d9447983",
    "BUNDLE_GRAPH_OK", 531
  ),
  (
    "bundle-bad-reference", "4aabcfa54309c83052d62b4fdcf1c6635a6cd3d937551e2ab947899345f9f082",
    "INVALID_REFERENCE", 528
  ),
  (
    "bundle-duplicate", "813f8a3b8fee59ba74abdb293c6cac5cca103b390153730e6e3bc4656540f15b",
    "DUPLICATE_ENTRY", 531
  ),
  (
    "bundle-wrong-type", "293c10c8abf055e8c1f84bae4913c7246bf9be5bf53dee0fb3c918e32a8346a7",
    "INVALID_BUNDLE_TYPE", 532
  ),
  (
    "bundle-linked", "1d24976b74ab0481ce2acc1010d58ec5e4b9da9ba93071e1042afeb299a03d88",
    "BUNDLE_GRAPH_OK", 559
  ),
  (
    "bundle-dangling", "1bbc0bac94b3ff19dce3502164f3243748cf5aa7e869433bdb09e7ec2266b229",
    "INVALID_REFERENCE", 559
  ),
]
for item in cases {
  let name = "\(item.id) (\(item.bytes) bytes)"
  var selector: Node?
  for _ in 0..<30 {
    let found = matched(nodes(), kAXCheckBoxRole as String, name)
    if found.count == 1 {
      selector = found[0]
      break
    }
    Thread.sleep(forTimeInterval: 0.2)
  }
  guard let selector else { refuse("new AX selector missing or ambiguous: \(name)") }
  perform(selector, name)
  Thread.sleep(forTimeInterval: 0.15)
  let verify = matched(nodes(), kAXButtonRole as String, "Verify synthetic SHA-256")
  guard verify.count == 1 else { refuse("original Verify button missing or ambiguous") }
  perform(verify[0], "Verify synthetic SHA-256")

  let exactSHA = "Synthetic raw SHA-256 verified: \(item.sha)"
  let exactStatus = "Fictional FHIR envelope: \(item.status) (NOT full FHIR R4 validation)"
  var success = false
  for _ in 0..<30 {
    let current = nodes()
    let readableSHA = current.filter {
      $0.role == (kAXStaticTextRole as String) && $0.labels.contains(exactSHA)
    }
    let readableStatus = current.filter {
      $0.role == (kAXStaticTextRole as String) && $0.labels.contains(exactStatus)
    }
    if readableSHA.count == 1 && readableStatus.count == 1 {
      success = true
      break
    }
    Thread.sleep(forTimeInterval: 0.15)
  }
  guard success else {
    let preview = matched(nodes(), nil, "Fictional FHIR envelope").map {
      "\($0.role):\($0.labels.joined(separator: "|"))"
    }
    refuse("separate accessible SHA/structural status missing for \(item.id) AX=\(preview)")
  }
  print("MACOS_D2_FHIR_AX_FIXTURE_PASS \(item.id) status=\(item.status)")
}
print("MACOS_D2_FHIR_AX_8_OF_8_PASS_NONPUBLISHING")
