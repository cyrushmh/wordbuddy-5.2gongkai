puts "LANG=Ruby"
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
