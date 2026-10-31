$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'windows-egress-window-functions.ps1')
function Assert([bool]$Pass, [string]$Case) {
    if(-not $Pass) { throw "D1_WINDOW_SELFTEST_FAIL: $Case" }
    Write-Output "PASS D1_EGRESS_WINDOW_$Case"
}
$rows=@(
    [pscustomobject]@{ProcessId=7001;ParentProcessId=0},
    [pscustomobject]@{ProcessId=7002;ParentProcessId=7001},
    [pscustomobject]@{ProcessId=7003;ParentProcessId=7002},
    [pscustomobject]@{ProcessId=8000;ParentProcessId=0},
    [pscustomobject]@{ProcessId=8001;ParentProcessId=8000}
)
$tree=Get-D1ProcessTree -Processes $rows -RootPid 7001
Assert ($tree.Count -eq 3 -and $tree.Contains(7003) -and -not $tree.Contains(8001)) 'NESTED_TREE_SCOPE'
try {
    $null=Get-D1ProcessTree -Processes $rows -RootPid 123456
    Assert $false 'MISSING_ROOT'
} catch {
    Assert ($_.Exception.Message -like '*D1_WINDOW_ROOT_ABSENT*') 'MISSING_ROOT_REJECTED'
}
$allowed=@(
    [pscustomobject]@{OwningProcess=7003;State='Established';RemoteAddress='127.0.0.1';RemotePort=80},
    [pscustomobject]@{OwningProcess=7002;State='SynSent';RemoteAddress='127.0.0.2';RemotePort=81},
    [pscustomobject]@{OwningProcess=7002;State='Established';RemoteAddress='::1';RemotePort=82},
    [pscustomobject]@{OwningProcess=7002;State='Established';RemoteAddress='::ffff:127.0.0.1';RemotePort=82},
    [pscustomobject]@{OwningProcess=7003;State='Listen';RemoteAddress='0.0.0.0';RemotePort=0},
    [pscustomobject]@{OwningProcess=8001;State='Established';RemoteAddress='8.8.8.8';RemotePort=443}
)
$g=@(Get-D1ExternalTcp -TreePids $tree -Connections $allowed)
Assert ($g.Count -eq 0) 'LOOPBACK_VARIANTS_AND_UNRELATED'
$cases=@(
    @{name='external-ipv4';state='Established';address='8.8.8.8'},
    @{name='external-ipv6';state='Established';address='2001:db8::123'},
    @{name='external-synsent';state='SynSent';address='203.0.113.1'},
    @{name='external-grandchild';state='TimeWait';address='2001:db8::10'},
    @{name='wildcard-established';state='Established';address='0.0.0.0'},
    @{name='unparseable';state='Established';address='unexpected.invalid'},
    @{name='missing-address';state='Established';address=''},
    @{name='mapped-external';state='Established';address='::ffff:203.0.113.7'}
)
foreach($case in $cases) {
    $entry=[pscustomobject]@{
        OwningProcess=7003;State=$case.state;RemoteAddress=$case.address;RemotePort=443
    }
    $result=@(Get-D1ExternalTcp -TreePids $tree -Connections @($entry))
    Assert ($result.Count -eq 1) $case.name.ToUpperInvariant()
}
# Simulated time-window driver: first frame clean, second frame exposes TCP;
# a single-shot snapshot would miss it. No network requests are made.
$first=@(Get-D1ExternalTcp -TreePids $tree -Connections $allowed)
$second=@(Get-D1ExternalTcp -TreePids $tree -Connections @(
    [pscustomobject]@{OwningProcess=7002;State='SynSent';RemoteAddress='2001:db8::a';RemotePort=443}
))
Assert ($first.Count -eq 0 -and $second.Count -eq 1) 'DELAYED_SECOND_SAMPLE_REJECTED'
Write-Output 'D1_EGRESS_WINDOW_SYNTHETIC_12_OF_12_PASS_NOT_OS_EGRESS_PROOF'
