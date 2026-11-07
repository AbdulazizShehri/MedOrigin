//! Experimental, synthetic-only benchmark of the full Rust D0 public API.
//! Unlike the Python reference raw-digest microbenchmark this API also
//! allocates fixture bytes and formats the digest, so timing is NOT a
//! like-for-like cross-language speedup claim. No RSS is measured.
use medorigin_desktop_d0_rust_prototype::hash_fixture_raw_v1;
use std::hint::black_box;
use std::time::Instant;

fn main() {
    const ITERATIONS: usize = 512;
    let cases = [
        "patient-minimal",
        "patient-invalid-utf8",
        "patient-over-limit",
        "patient-exact-limit",
    ];
    println!("scope=EXPERIMENTAL_RUST_API_WITH_ALLOC_AND_HEX");
    println!("platform={}", std::env::consts::OS);
    println!("iterations={ITERATIONS}; rust_release_expected=true; rss=not_measured");
    println!("rust_parity_production_qualified=false; publication_authorized=false");
    for id in cases {
        for _ in 0..16 {
            black_box(hash_fixture_raw_v1(id, 65_536).expect("known fixture"));
        }
        let mut elapsed = Vec::with_capacity(ITERATIONS);
        for _ in 0..ITERATIONS {
            let before = Instant::now();
            let outcome =
                hash_fixture_raw_v1(black_box(id), 65_536).expect("known synthetic fixture");
            black_box(outcome);
            elapsed.push(before.elapsed().as_nanos());
        }
        elapsed.sort_unstable();
        let median = (elapsed[255] + elapsed[256]) / 2;
        let p95 = elapsed[(ITERATIONS * 95).div_ceil(100) - 1];
        println!("{id}: median_ns={median}; p95_ns={p95}");
    }
}
