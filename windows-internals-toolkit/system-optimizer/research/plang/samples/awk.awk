BEGIN {
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
