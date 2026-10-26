import threading, os, tempfile
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
