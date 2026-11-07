import ApplicationServices
import Foundation

// Read the sentinel from the ACTUAL native D2 GUI AX tree, not from a helper.
guard
  CommandLine.arguments.count == 2
    || (CommandLine.arguments.count == 3
      && CommandLine.arguments[2] == "--expect-unconfined-allowed"),
  let pid = Int32(CommandLine.arguments[1]), pid > 0
else {
  fputs("D2_SELF_EGRESS_NO_GO: expected real native app PID\n", stderr)
  exit(2)
}
guard AXIsProcessTrusted() else {
  fputs("D2_SELF_EGRESS_NO_GO: macOS Accessibility permission is required\n", stderr)
  exit(1)
}
let app = AXUIElementCreateApplication(pid)
let unconfinedControl = CommandLine.arguments.count == 3
let expected =
  unconfinedControl
  ? "D2_SELF_SANDBOX_PROBE_UNEXPECTED_NETWORK_ALLOWED_NO_GO"
  : "D2_SELF_PROCESS_APP_SANDBOX_LOOPBACK_DENIED_EPERM"
var observed = [String]()
func scan(_ node: AXUIElement, depth: Int) {
  guard depth < 20, observed.count < 500 else { return }
  for attribute in [kAXTitleAttribute, kAXValueAttribute] {
    var value: CFTypeRef?
    if AXUIElementCopyAttributeValue(node, attribute as CFString, &value) == .success {
      if let value { observed.append(String(describing: value)) }
    }
  }
  var children: CFTypeRef?
  if AXUIElementCopyAttributeValue(node, kAXChildrenAttribute as CFString, &children) == .success,
    let nodes = children as? [AXUIElement]
  {
    for child in nodes { scan(child, depth: depth + 1) }
  }
}
for _ in 0..<25 {
  observed.removeAll()
  var value: CFTypeRef?
  if AXUIElementCopyAttributeValue(app, kAXWindowsAttribute as CFString, &value) == .success,
    let windows = value as? [AXUIElement], windows.count == 1
  {
    scan(windows[0], depth: 0)
    if observed.contains(where: { $0.contains(expected) }) {
      print(
        unconfinedControl
          ? "D2_SAME_BINARY_UNCONFINED_LOOPBACK_ALLOWED_CONTROL_PASS"
          : "D2_NATIVE_TEST_WRAPPER_LOOPBACK_EPERM_DENIAL_VISIBLE_IN_AX_PASS")
      exit(0)
    }
    if observed.contains(where: {
      (!unconfinedControl && $0.contains("D2_SELF_SANDBOX_PROBE_UNEXPECTED_NETWORK_ALLOWED_NO_GO"))
        || (unconfinedControl && $0.contains("D2_SELF_PROCESS_APP_SANDBOX_LOOPBACK_DENIED_EPERM"))
        || $0.contains("D2_SELF_SANDBOX_PROBE_INCONCLUSIVE_SOCKET_ERROR")
        || $0.contains("D2_SELF_SANDBOX_PROBE_INVALID_PORT")
        || $0.contains("D2_SELF_SANDBOX_PROBE_NOT_CONFIGURED")
    }) {
      fputs("D2_SELF_EGRESS_NO_GO: actual D2 process did not receive EPERM\n", stderr)
      exit(1)
    }
  }
  Thread.sleep(forTimeInterval: 0.2)
}
fputs(
  "D2_SELF_EGRESS_NO_GO: expected OS-denied loopback result absent from native D2 AX tree\n", stderr
)
exit(1)
