puts "LANG=Tcl"
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
