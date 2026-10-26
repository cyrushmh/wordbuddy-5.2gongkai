package main

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
	fmt.Printf("LITERALS=%d,%s,%t,%v\n", x, s, b, n)
	fmt.Printf("OPS=%d\n", 7*6+len("abc"))
	acc := 0
	for i := 1; i < 6; i++ { acc += i }
	fmt.Printf("CONTROL=%d\n", acc)
	fmt.Printf("FUNC=%d\n", fact(5))
	arr := []int{1, 2, 3}
	d := map[string]int{"a": 1}
	fmt.Printf("DATA=%d,%d\n", len(arr), d["a"])
	p := filepath.Join(os.TempDir(), "plang_go.txt")
	os.WriteFile(p, []byte("io"), 0644)
	os.ReadFile(p)
	os.Remove(p)
	fmt.Println("IO=ok")
	if _, err := os.Open("/nonexistent/plang"); err != nil {
		fmt.Printf("ERROR=%T\n", err)
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
	fmt.Printf("CONCURRENCY=%v\n", res)
}
