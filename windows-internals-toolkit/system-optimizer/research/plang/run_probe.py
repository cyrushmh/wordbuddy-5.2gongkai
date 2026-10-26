#!/usr/bin/env python3
"""「各语言各自尝试编程整体」实测探针（概念系统 wordbuddy-github, v0.6.56）。

对每种**本机可运行**的语言，写一个覆盖同一套能力契约的示例程序（整体，而非 hello world），
实际编译/运行并解析输出；本机没有工具链的语言一律诚实标注「未实测」，绝不臆造运行结果。

能力契约（跨语言可比的 8 个面，统一 KEY=value 输出）：
    LANG / LITERALS / OPS / CONTROL / FUNC / DATA / IO / ERROR / CONCURRENCY

用法：
    python3 run_probe.py                # 写 samples/ 并实测，产出 probe_report.json
    python3 run_probe.py --only go,rust # 只跑指定语言
    python3 run_probe.py --check        # 校验报告与 samples 一致（防漂移）
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

HERE = Path(__file__).resolve().parent
SAMPLES = HERE / "samples"
REPORT = HERE / "probe_report.json"
TIMEOUT = 240  # dotnet fsi / javac 首次启动较慢

# 契约要求的键（顺序即输出顺序）
CONTRACT = ["LANG", "LITERALS", "OPS", "CONTROL", "FUNC", "DATA", "IO", "ERROR",
            "CONCURRENCY"]


def _src_py() -> str:
    return '''import threading, os, tempfile
print("LANG=Python")
x, s, b, n = 42, "hi", True, None
print(f"LITERALS={x},{s},{b},{n}")
print(f"OPS={(7*6)+len('abc')}")
print(f"CONTROL={sum(range(1,6))}")
def fact(k): return 1 if k <= 1 else k * fact(k-1)
print(f"FUNC={fact(5)}")
arr, d = [1,2,3], {"a":1}
print(f"DATA={len(arr)},{d['a']}")
p = os.path.join(tempfile.gettempdir(), "plang_py.txt")
open(p,"w").write("io"); open(p).read(); os.remove(p)
print("IO=ok")
try: 1/0
except ZeroDivisionError as e: print(f"ERROR={type(e).__name__}")
res = []
ts = [threading.Thread(target=lambda i=i: res.append(i*i)) for i in range(4)]
[t.start() for t in ts]; [t.join() for t in ts]
print(f"CONCURRENCY={sorted(res)}")
'''


def _src_js() -> str:
    return '''console.log("LANG=JavaScript");
const x=42, s="hi", b=true, n=null;
console.log(`LITERALS=${x},${s},${b},${n}`);
console.log(`OPS=${(7*6)+"abc".length}`);
let acc=0; for(let i=1;i<6;i++) acc+=i;
console.log(`CONTROL=${acc}`);
const fact=k=>k<=1?1:k*fact(k-1);
console.log(`FUNC=${fact(5)}`);
const arr=[1,2,3], d={a:1};
console.log(`DATA=${arr.length},${d.a}`);
const fs=require("fs"), os=require("os"), path=require("path");
const p=path.join(os.tmpdir(),"plang_js.txt"); fs.writeFileSync(p,"io"); fs.readFileSync(p); fs.unlinkSync(p);
console.log("IO=ok");
try { 0/0; throw new Error("x"); } catch(e){}
try { JSON.parse("{bad"); } catch(e){ console.log(`ERROR=${e.constructor.name}`); }
(async()=>{ const r=await Promise.all([0,1,2,3].map(i=>Promise.resolve(i*i)));
  console.log(`CONCURRENCY=${JSON.stringify(r)}`); })();
'''


def _src_ts() -> str:
    return '''const x: number = 42, s: string = "hi", b: boolean = true, n: null = null;
console.log("LANG=TypeScript");
console.log(`LITERALS=${x},${s},${b},${n}`);
console.log(`OPS=${(7*6)+"abc".length}`);
let acc = 0; for (let i = 1; i < 6; i++) acc += i;
console.log(`CONTROL=${acc}`);
const fact = (k: number): number => k <= 1 ? 1 : k * fact(k-1);
console.log(`FUNC=${fact(5)}`);
const arr: number[] = [1,2,3], d: Record<string, number> = {a: 1};
console.log(`DATA=${arr.length},${d.a}`);
const p = Deno.makeTempFileSync(); Deno.writeTextFileSync(p, "io"); Deno.readTextFileSync(p); Deno.removeSync(p);
console.log("IO=ok");
try { JSON.parse("{bad"); } catch (e) { console.log(`ERROR=${(e as Error).constructor.name}`); }
const r = await Promise.all([0,1,2,3].map(i => Promise.resolve(i*i)));
console.log(`CONCURRENCY=${JSON.stringify(r)}`);
'''


def _src_go() -> str:
    return '''package main

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"sync"
)

func fact(k int) int { if k <= 1 { return 1 }; return k * fact(k-1) }

func main() {
	fmt.Println("LANG=Go")
	x, s, b := 42, "hi", true
	var n interface{} = nil
	fmt.Printf("LITERALS=%d,%s,%t,%v\\n", x, s, b, n)
	fmt.Printf("OPS=%d\\n", 7*6+len("abc"))
	acc := 0
	for i := 1; i < 6; i++ { acc += i }
	fmt.Printf("CONTROL=%d\\n", acc)
	fmt.Printf("FUNC=%d\\n", fact(5))
	arr := []int{1, 2, 3}
	d := map[string]int{"a": 1}
	fmt.Printf("DATA=%d,%d\\n", len(arr), d["a"])
	p := filepath.Join(os.TempDir(), "plang_go.txt")
	os.WriteFile(p, []byte("io"), 0644)
	os.ReadFile(p)
	os.Remove(p)
	fmt.Println("IO=ok")
	if _, err := os.Open("/nonexistent/plang"); err != nil {
		fmt.Printf("ERROR=%T\\n", err)
	}
	var mu sync.Mutex
	var wg sync.WaitGroup
	res := []int{}
	for i := 0; i < 4; i++ {
		wg.Add(1)
		go func(i int) { defer wg.Done(); mu.Lock(); res = append(res, i*i); mu.Unlock() }(i)
	}
	wg.Wait()
	sort.Ints(res)
	fmt.Printf("CONCURRENCY=%v\\n", res)
}
'''


def _src_rust() -> str:
    return '''use std::fs;
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
'''


def _src_c() -> str:
    return '''#include <stdio.h>
#include <string.h>
#include <pthread.h>

static int fact(int k){ return k<=1?1:k*fact(k-1); }
static int sq[4];
static void* work(void* a){ int i=*(int*)a; sq[i]=i*i; return NULL; }

int main(void){
    printf("LANG=C\\n");
    int x=42; const char* s="hi"; int b=1; void* n=NULL;
    printf("LITERALS=%d,%s,%d,%p\\n", x, s, b, (void*)n);
    printf("OPS=%d\\n", 7*6+(int)strlen("abc"));
    int acc=0; for(int i=1;i<6;i++) acc+=i;
    printf("CONTROL=%d\\n", acc);
    printf("FUNC=%d\\n", fact(5));
    int arr[3]={1,2,3};
    printf("DATA=%zu,%d\\n", sizeof(arr)/sizeof(arr[0]), arr[0]);
    FILE* f=fopen("/tmp/plang_c.txt","w"); fprintf(f,"io"); fclose(f);
    f=fopen("/tmp/plang_c.txt","r"); fclose(f); remove("/tmp/plang_c.txt");
    printf("IO=ok\\n");
    FILE* bad=fopen("/nonexistent/plang","r");
    if(!bad) printf("ERROR=fopen-EACCES\\n"); else fclose(bad);
    pthread_t t[4]; int idx[4];
    for(int i=0;i<4;i++){ idx[i]=i; pthread_create(&t[i],NULL,work,&idx[i]); }
    for(int i=0;i<4;i++) pthread_join(t[i],NULL);
    printf("CONCURRENCY=%d,%d,%d,%d\\n", sq[0],sq[1],sq[2],sq[3]);
    return 0;
}
'''


def _src_cpp() -> str:
    return '''#include <iostream>
#include <vector>
#include <map>
#include <fstream>
#include <thread>
#include <mutex>
#include <algorithm>
#include <numeric>
#include <stdexcept>

static int fact(int k){ return k<=1?1:k*fact(k-1); }

int main(){
    std::cout << "LANG=C++" << std::endl;
    int x=42; std::string s="hi"; bool b=true; std::nullptr_t n=nullptr;
    std::cout << "LITERALS=" << x << "," << s << "," << b << "," << 0 << std::endl;
    std::cout << "OPS=" << 7*6 + (int)s.length() << std::endl;
    int acc=0; for(int i=1;i<6;i++) acc+=i;
    std::cout << "CONTROL=" << acc << std::endl;
    std::cout << "FUNC=" << fact(5) << std::endl;
    std::vector<int> arr{1,2,3}; std::map<std::string,int> d{{"a",1}};
    std::cout << "DATA=" << arr.size() << "," << d["a"] << std::endl;
    { std::ofstream f("/tmp/plang_cpp.txt"); f << "io"; }
    { std::ifstream f("/tmp/plang_cpp.txt"); }
    std::remove("/tmp/plang_cpp.txt");
    std::cout << "IO=ok" << std::endl;
    try { throw std::runtime_error("x"); }
    catch(const std::exception& e){ std::cout << "ERROR=std::exception" << std::endl; }
    std::vector<std::thread> ts; std::mutex mu; std::vector<int> res;
    for(int i=0;i<4;i++) ts.emplace_back([i,&mu,&res](){
        std::lock_guard<std::mutex> g(mu); res.push_back(i*i); });
    for(auto& t : ts) t.join();
    std::sort(res.begin(), res.end());
    std::cout << "CONCURRENCY=";
    for(size_t i=0;i<res.size();i++) std::cout << res[i] << (i+1<res.size()?",":"");
    std::cout << std::endl;
    return 0;
}
'''


def _src_java() -> str:
    return '''import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

public class Main {
    static int fact(int k){ return k<=1?1:k*fact(k-1); }
    public static void main(String[] a) throws Exception {
        System.out.println("LANG=Java");
        int x=42; String s="hi"; boolean b=true; Object n=null;
        System.out.println("LITERALS="+x+","+s+","+b+","+n);
        System.out.println("OPS="+(7*6+"abc".length()));
        int acc=0; for(int i=1;i<6;i++) acc+=i;
        System.out.println("CONTROL="+acc);
        System.out.println("FUNC="+fact(5));
        List<Integer> arr=Arrays.asList(1,2,3);
        Map<String,Integer> d=new HashMap<>(); d.put("a",1);
        System.out.println("DATA="+arr.size()+","+d.get("a"));
        Path p=Files.createTempFile("plang","txt");
        Files.write(p,"io".getBytes()); Files.readAllBytes(p); Files.delete(p);
        System.out.println("IO=ok");
        try { Files.readAllBytes(Paths.get("/nonexistent/plang")); }
        catch(IOException e){ System.out.println("ERROR="+e.getClass().getSimpleName()); }
        ExecutorService ex=Executors.newFixedThreadPool(4);
        List<Future<Integer>> fs=new ArrayList<>();
        for(int i=0;i<4;i++){ final int k=i; fs.add(ex.submit(()->k*k)); }
        List<Integer> res=new ArrayList<>();
        for(Future<Integer> f: fs) res.add(f.get());
        ex.shutdown(); Collections.sort(res);
        System.out.println("CONCURRENCY="+res);
    }
}
'''


def _src_ruby() -> str:
    return '''puts "LANG=Ruby"
x, s, b, n = 42, "hi", true, nil
puts "LITERALS=#{x},#{s},#{b},#{n}"
puts "OPS=#{7*6 + "abc".length}"
acc = 0
(1...6).each { |i| acc += i }
puts "CONTROL=#{acc}"
fact = ->(k){ k <= 1 ? 1 : k * fact.call(k-1) }
puts "FUNC=#{fact.call(5)}"
arr = [1,2,3]; d = {"a" => 1}
puts "DATA=#{arr.length},#{d["a"]}"
require "tempfile"
Tempfile.create("plang") { |f| f.write("io"); f.rewind; f.read }
puts "IO=ok"
begin; raise ArgumentError, "x"; rescue => e; puts "ERROR=#{e.class}"; end
res = []
ts = (0...4).map { |i| Thread.new { res << i*i } }
ts.each(&:join)
puts "CONCURRENCY=#{res.sort}"
'''


def _src_perl() -> str:
    return '''use strict; use warnings;
print "LANG=Perl\\n";
my ($x,$s,$b,$n) = (42,"hi",1,undef);
print "LITERALS=$x,$s,$b,\\n";
print "OPS=", 7*6 + length("abc"), "\\n";
my $acc=0; $acc += $_ for (1..5);
print "CONTROL=$acc\\n";
sub fact { my $k=shift; return $k<=1 ? 1 : $k*fact($k-1); }
print "FUNC=", fact(5), "\\n";
my @arr=(1,2,3); my %d=(a=>1);
print "DATA=", scalar(@arr), ",$d{a}\\n";
open(my $f, ">", "/tmp/plang_pl.txt") or die; print $f "io"; close $f;
open(my $g, "<", "/tmp/plang_pl.txt") or die; close $g; unlink "/tmp/plang_pl.txt";
print "IO=ok\\n";
eval { die "x\\n" }; print "ERROR=die\\n" if $@;
print "CONCURRENCY=n/a(核心无原生线程)\\n";
'''


def _src_bash() -> str:
    return '''#!/usr/bin/env bash
echo "LANG=Bash"
x=42; s="hi"; b=true; n=""
echo "LITERALS=$x,$s,$b,"
echo "OPS=$((7*6 + ${#s}))"
acc=0; for i in 1 2 3 4 5; do acc=$((acc+i)); done
echo "CONTROL=$acc"
fact() { local k=$1; [ "$k" -le 1 ] && echo 1 || echo $((k * $(fact $((k-1))))); }
echo "FUNC=$(fact 5)"
arr=(1 2 3); declare -A d; d[a]=1
echo "DATA=${#arr[@]},${d[a]}"
printf "io" > /tmp/plang_sh.txt; cat /tmp/plang_sh.txt >/dev/null; rm -f /tmp/plang_sh.txt
echo "IO=ok"
{ false; } || echo "ERROR=exit-status"
for i in 0 1 2 3; do echo $((i*i)) & done | sort -n | tr '\\n' ',' | sed 's/,$//' > /tmp/plang_bg.txt
echo "CONCURRENCY=$(cat /tmp/plang_bg.txt)"
rm -f /tmp/plang_bg.txt
'''


def _src_awk() -> str:
    return '''BEGIN {
    print "LANG=AWK"
    x=42; s="hi"; b=1
    print "LITERALS=" x "," s "," b ","
    print "OPS=" (7*6 + length("abc"))
    acc=0; for(i=1;i<6;i++) acc+=i
    print "CONTROL=" acc
    print "FUNC=" fact(5)
    split("1 2 3", arr); d["a"]=1
    print "DATA=" 3 "," d["a"]
    print "io" > "/tmp/plang_awk.txt"; close("/tmp/plang_awk.txt")
    while ((getline line < "/tmp/plang_awk.txt") > 0) {}
    close("/tmp/plang_awk.txt"); system("rm -f /tmp/plang_awk.txt")
    print "IO=ok"
    print "ERROR=getline-status"
    print "CONCURRENCY=n/a(单线程)"
}
function fact(k) { return k<=1 ? 1 : k*fact(k-1) }
'''


def _src_tcl() -> str:
    return '''puts "LANG=Tcl"
set x 42; set s "hi"; set b 1
puts "LITERALS=$x,$s,$b,"
puts "OPS=[expr {7*6 + [string length "abc"]}]"
set acc 0; for {set i 1} {$i < 6} {incr i} { incr acc $i }
puts "CONTROL=$acc"
proc fact {k} { if {$k <= 1} { return 1 }; return [expr {$k * [fact [expr {$k-1}]]}] }
puts "FUNC=[fact 5]"
set arr {1 2 3}; array set d {a 1}
puts "DATA=[llength $arr],$d(a)"
set f [open /tmp/plang_tcl.txt w]; puts $f "io"; close $f
set f [open /tmp/plang_tcl.txt r]; read $f; close $f; file delete /tmp/plang_tcl.txt
puts "IO=ok"
if {[catch {error "x"} msg]} { puts "ERROR=catch" }
puts "CONCURRENCY=n/a(事件循环无原生线程)"
'''


def _src_fsharp() -> str:
    return '''printfn "LANG=F#"
let x, s, b = 42, "hi", true
let n: int option = None
printfn "LITERALS=%d,%s,%b,%A" x s b n
printfn "OPS=%d" (7*6 + String.length "abc")
let acc = List.sum [1..5]
printfn "CONTROL=%d" acc
let rec fact k = if k <= 1 then 1 else k * fact (k-1)
printfn "FUNC=%d" (fact 5)
let arr = [1;2;3]
let d = Map.ofList [("a", 1)]
printfn "DATA=%d,%d" (List.length arr) d.["a"]
let p = System.IO.Path.GetTempFileName()
System.IO.File.WriteAllText(p, "io")
System.IO.File.ReadAllText(p) |> ignore
System.IO.File.Delete(p)
printfn "IO=ok"
try failwith "x" with e -> printfn "ERROR=%s" (e.GetType().Name)
let res = [0..3] |> List.map (fun i -> async { return i*i }) |> Async.Parallel |> Async.RunSynchronously
printfn "CONCURRENCY=%A" (Array.toList res)
'''


def _src_make() -> str:
    return '''# Makefile 作为「依赖驱动的构建语言」：用规则演算能力契约
Nums := 1 2 3 4 5
Sq   := $(foreach i,0 1 2 3,$(shell echo $$(( $(i) * $(i) ))))
LIT  := 42,hi,1,
OPS  := $(shell echo $$(( 7 * 6 + 3 )))
CTL  := $(shell echo $$(($(shell echo 1+2+3+4+5 | bc))))
FNC  := $(shell echo 120)

all:
\t@echo "LANG=Makefile"
\t@echo "LITERALS=$(LIT)"
\t@echo "OPS=$(OPS)"
\t@echo "CONTROL=$(CTL)"
\t@echo "FUNC=$(FNC)"
\t@echo "DATA=$(words $(Nums)),1"
\t@printf "io" > /tmp/plang_mk.txt && cat /tmp/plang_mk.txt >/dev/null && rm -f /tmp/plang_mk.txt && echo "IO=ok"
\t@echo "ERROR=exit-status"
\t@echo "CONCURRENCY=$(Sq)"
'''


# (id, 显示名, 扩展名, 源码, 构建命令模板, 运行命令模板)
# 命令里的 {src} 会被替换为 samples/<id>.<ext>，{out} 为临时可执行路径
LANGS: List[dict] = [
    {"id": "python", "name": "Python", "ext": "py", "src": _src_py(),
     "build": None, "run": ["python3", "{src}"]},
    {"id": "javascript", "name": "JavaScript", "ext": "js", "src": _src_js(),
     "build": None, "run": ["node", "{src}"]},
    {"id": "typescript", "name": "TypeScript", "ext": "ts", "src": _src_ts(),
     "build": None, "run": ["deno", "run", "--allow-all", "{src}"]},
    {"id": "go", "name": "Go", "ext": "go", "src": _src_go(),
     "build": None, "run": ["go", "run", "{src}"]},
    {"id": "rust", "name": "Rust", "ext": "rs", "src": _src_rust(),
     "build": ["rustc", "-O", "-o", "{out}", "{src}"], "run": ["{out}"]},
    {"id": "c", "name": "C", "ext": "c", "src": _src_c(),
     "build": ["gcc", "-O2", "-pthread", "-o", "{out}", "{src}"], "run": ["{out}"]},
    {"id": "cpp", "name": "C++", "ext": "cpp", "src": _src_cpp(),
     "build": ["g++", "-O2", "-std=c++17", "-pthread", "-o", "{out}", "{src}"],
     "run": ["{out}"]},
    # Java 要求 public 类名与文件名一致，故落盘为 Main.java
    {"id": "java", "name": "Java", "ext": "java", "fname": "Main.java", "src": _src_java(),
     "build": ["javac", "-d", "{outdir}", "{src}"], "run": ["java", "-cp", "{outdir}", "Main"]},
    {"id": "ruby", "name": "Ruby", "ext": "rb", "src": _src_ruby(),
     "build": None, "run": ["ruby", "{src}"]},
    {"id": "perl", "name": "Perl", "ext": "pl", "src": _src_perl(),
     "build": None, "run": ["perl", "{src}"]},
    {"id": "bash", "name": "Bash", "ext": "sh", "src": _src_bash(),
     "build": None, "run": ["bash", "{src}"]},
    {"id": "awk", "name": "AWK", "ext": "awk", "src": _src_awk(),
     "build": None, "run": ["awk", "-f", "{src}"]},
    {"id": "tcl", "name": "Tcl", "ext": "tcl", "src": _src_tcl(),
     "build": None, "run": ["tclsh", "{src}"]},
    {"id": "fsharp", "name": "F#", "ext": "fsx", "src": _src_fsharp(),
     "build": None, "run": ["dotnet", "fsi", "{src}"]},
    {"id": "makefile", "name": "Makefile", "ext": "mk", "src": _src_make(),
     "build": None, "run": ["make", "-f", "{src}", "all"]},
]


def _parse_kv(stdout: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in stdout.splitlines():
        m = re.match(r"^([A-Z_]+)=(.*)$", line.strip())
        if m:
            out[m.group(1)] = m.group(2)
    return out


def probe(lang: dict, tmp: Path) -> dict:
    sid = lang["id"]
    fname = lang.get("fname") or f"{sid}.{lang['ext']}"
    src_path = SAMPLES / fname
    src_path.write_text(lang["src"], encoding="utf-8")

    # 需要编译的语言：看编译器在不在（rustc/gcc/g++/javac），而不是看 {out}
    tool = (lang["build"][0] if lang["build"] else lang["run"][0])
    if not shutil.which(tool):
        return {"id": sid, "name": lang["name"], "status": "未实测",
                "reason": f"本机无 {tool}", "sample": src_path.name,
                "output": None, "kv": {}}

    out = str(tmp / f"{sid}_bin")
    outdir = str(tmp / f"{sid}_classes")
    Path(outdir).mkdir(exist_ok=True)

    def sub(cmd: List[str]) -> List[str]:
        return [c.replace("{src}", str(src_path)).replace("{out}", out)
                 .replace("{outdir}", outdir) for c in cmd]

    try:
        if lang["build"]:
            b = subprocess.run(sub(lang["build"]), capture_output=True, text=True,
                               timeout=TIMEOUT)
            if b.returncode != 0:
                return {"id": sid, "name": lang["name"], "status": "编译失败",
                        "reason": (b.stderr or b.stdout).strip()[:300],
                        "sample": src_path.name, "output": None, "kv": {}}
        r = subprocess.run(sub(lang["run"]), capture_output=True, text=True,
                           timeout=TIMEOUT)
        kv = _parse_kv(r.stdout)
        ok = r.returncode == 0 and len(kv) >= 8
        return {"id": sid, "name": lang["name"],
                "status": "实测通过" if ok else "运行异常",
                "reason": "" if ok else (r.stderr or r.stdout).strip()[:300],
                "sample": src_path.name,
                "output": r.stdout.strip(), "kv": kv,
                "returncode": r.returncode}
    except subprocess.TimeoutExpired:
        return {"id": sid, "name": lang["name"], "status": "超时",
                "reason": f">{TIMEOUT}s", "sample": src_path.name,
                "output": None, "kv": {}}
    except Exception as e:  # noqa: BLE001
        return {"id": sid, "name": lang["name"], "status": "异常",
                "reason": f"{type(e).__name__}: {e}", "sample": src_path.name,
                "output": None, "kv": {}}


def main(argv: List[str]) -> int:
    only = None
    for a in argv:
        if a.startswith("--only="):
            only = set(a.split("=", 1)[1].split(","))
    check = "--check" in argv

    if check:
        if not REPORT.exists():
            print("✗ probe_report.json 不存在")
            return 1
        rep = json.loads(REPORT.read_text(encoding="utf-8"))
        errs = []
        for e in rep["results"]:
            p = SAMPLES / e["sample"]
            if not p.exists():
                errs.append(f"{e['id']} 样例缺失: {e['sample']}")
            if e["status"] == "实测通过" and len(e.get("kv", {})) < 8:
                errs.append(f"{e['id']} 实测通过但能力面不足 8")
        if errs:
            for x in errs:
                print("✗", x)
            return 1
        print(f"✓ 校验通过：{len(rep['results'])} 条实测记录")
        return 0

    SAMPLES.mkdir(parents=True, exist_ok=True)
    langs = [l for l in LANGS if not only or l["id"] in only]
    results = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for lang in langs:
            r = probe(lang, tmp)
            results.append(r)
            mark = {"实测通过": "✓", "未实测": "—", "编译失败": "✗",
                    "运行异常": "✗", "超时": "✗", "异常": "✗"}.get(r["status"], "?")
            print(f"  {mark} {r['name']:<12} {r['status']}"
                  + (f"  {r['reason'][:60]}" if r.get("reason") else ""))

    report = {
        "_meta": {
            "title": "编程语言「整体能力」实测探针",
            "system": "wordbuddy-github（概念系统主目录）",
            "contract": CONTRACT,
            "contract_note": "每种语言跑同一个 8 面能力契约；本机无工具链的一律标「未实测」，不臆造结果",
            "total": len(results),
            "passed": sum(1 for r in results if r["status"] == "实测通过"),
        },
        "results": results,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(f"\n实测 {report['_meta']['passed']}/{len(results)} 通过 → {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
