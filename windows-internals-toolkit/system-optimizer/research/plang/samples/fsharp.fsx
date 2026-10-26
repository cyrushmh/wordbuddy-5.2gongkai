printfn "LANG=F#"
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
