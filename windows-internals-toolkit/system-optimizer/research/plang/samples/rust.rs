use std::fs;
use std::thread;

fn fact(k: u64) -> u64 { if k <= 1 { 1 } else { k * fact(k - 1) } }

fn main() {
    println!("LANG=Rust");
    let (x, s, b) = (42, "hi", true);
    let n: Option<i32> = None;
    println!("LITERALS={},{},{},{:?}", x, s, b, n);
    println!("OPS={}", 7 * 6 + "abc".len());
    let mut acc = 0;
    for i in 1..6 { acc += i; }
    println!("CONTROL={}", acc);
    println!("FUNC={}", fact(5));
    let arr = vec![1, 2, 3];
    let mut d = std::collections::HashMap::new();
    d.insert("a", 1);
    println!("DATA={},{}", arr.len(), d["a"]);
    let p = std::env::temp_dir().join("plang_rs.txt");
    fs::write(&p, "io").unwrap();
    fs::read_to_string(&p).unwrap();
    fs::remove_file(&p).unwrap();
    println!("IO=ok");
    match fs::read_to_string("/nonexistent/plang") {
        Ok(_) => {}
        Err(e) => println!("ERROR={:?}", e.kind()),
    }
    let hs: Vec<_> = (0..4)
        .map(|i| thread::spawn(move || i * i))
        .collect();
    let mut res: Vec<i32> = hs.into_iter().map(|h| h.join().unwrap()).collect();
    res.sort();
    println!("CONCURRENCY={:?}", res);
}
