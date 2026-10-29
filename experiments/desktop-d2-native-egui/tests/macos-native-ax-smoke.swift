// Real macOS AX acceptance, synthetic-only D2, no screenshots or network.
// Must be run in an interactive trusted macOS user session against the
// approved native D2 preview PID. Headless CI only syntax-checks this source.
import ApplicationServices
import Foundation

let expected: [(name: String, sha: String)] = [
    ("patient-minimal (57 bytes)", "747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0"),
    ("patient-invalid-utf8 (1 bytes)", "a8100ae6aa1940d0b663bb31cd466142ebbdbd5187131b92d93818987832eb89"),
    ("patient-over-limit (32769 bytes)", "b929f15ca4f3fa28f54991ed0cb8ac5f430e388ee08bf401a853d8af91e44538"),
    ("patient-exact-limit (32768 bytes)", "ea711ce560191a81c0722c4a26592e0e2d9abb2186b6fd3af6897cd89d417d4e"),
]
let verifyName = "Verify synthetic SHA-256"

func read(_ element: AXUIElement, _ attribute: String) -> CFTypeRef? {
    var result: CFTypeRef?
    return AXUIElementCopyAttributeValue(element, attribute as CFString, &result) == .success
        ? result : nil
}

func nameOf(_ element: AXUIElement) -> String {
    for attribute in [kAXTitleAttribute, kAXValueAttribute, kAXDescriptionAttribute] {
        if let value = read(element, attribute) as? String, !value.isEmpty {
            return value
        }
    }
    return ""
}

func allDescendants(of root: AXUIElement) -> [AXUIElement] {
    var output: [AXUIElement] = []
    var pending: [AXUIElement] = [root]
    while let next = pending.popLast() {
        output.append(next)
        if output.count > 350 { break }
        if let children = read(next, kAXChildrenAttribute) as? [AXUIElement] {
            pending.append(contentsOf: children)
        }
    }
    return output
}

func button(named name: String, in elements: [AXUIElement]) -> AXUIElement? {
    elements.first {
        (read($0, kAXRoleAttribute) as? String) == kAXButtonRole as String
            && nameOf($0) == name
    }
}

func selector(named name: String, in elements: [AXUIElement]) -> AXUIElement? {
    elements.first {
        (read($0, kAXRoleAttribute) as? String) == (kAXCheckBoxRole as String)
            && nameOf($0) == name
    }
}

func errorExit(_ reason: String) -> Never {
    fputs("D2_MAC_NATIVE_AX_NO_GO: " + reason + "\n", stderr)
    exit(2)
}

guard CommandLine.arguments.count == 2,
      let pid = Int32(CommandLine.arguments[1]), pid > 0
else { errorExit("expected one positive approved preview PID") }

guard AXIsProcessTrusted() else {
    errorExit("macOS accessibility authorization missing")
}
let app = AXUIElementCreateApplication(pid)
var firstWindow: AXUIElement?
for _ in 0..<40 {
    if let windows = read(app, kAXWindowsAttribute) as? [AXUIElement],
       let window = windows.first {
        firstWindow = window
        break
    }
    Thread.sleep(forTimeInterval: 0.25)
}
guard let window = firstWindow
else { errorExit("no accessible native MedOrigin window") }

var controls: [AXUIElement] = []
for _ in 0..<30 {
    controls = allDescendants(of: window)
    if expected.allSatisfy({ selector(named: $0.name, in: controls) != nil })
        && button(named: verifyName, in: controls) != nil {
        break
    }
    Thread.sleep(forTimeInterval: 0.25)
}

let visibleButtons = controls.filter {
    (read($0, kAXRoleAttribute) as? String) == kAXButtonRole as String
}.map(nameOf)
print("D2_MAC_AX_WINDOW_DESCENDANTS=\(controls.count)")
print("D2_MAC_AX_NAMED_BUTTONS=\(visibleButtons.filter { !$0.isEmpty }.count)")

guard let verify = button(named: verifyName, in: controls) else {
    errorExit("synthetic SHA verification control not exposed in NSAccessibility")
}
for fixture in expected {
    guard let selector = selector(named: fixture.name, in: controls) else {
        errorExit("missing selector control: \(fixture.name)")
    }
    guard AXUIElementPerformAction(selector, kAXPressAction as CFString) == .success else {
        errorExit("AXPress refused selector: \(fixture.name)")
    }
    guard AXUIElementPerformAction(verify, kAXPressAction as CFString) == .success else {
        errorExit("AXPress refused synthetic digest verification control")
    }
    let display = "Synthetic raw SHA-256 verified: " + fixture.sha
    var found = false
    for _ in 0..<40 {
        let tree = allDescendants(of: window)
        found = tree.contains { nameOf($0) == display }
        if found { break }
        Thread.sleep(forTimeInterval: 0.2)
    }
    if !found { errorExit("missing digest after actual AXPress for \(fixture.name)") }
    print("D2_MAC_NATIVE_AX_FIXTURE_PASS=\(fixture.name)")
}
print("D2_MAC_NATIVE_AX_4_OF_4_PASS (fictional fixtures; packet isolation unqualified)")
