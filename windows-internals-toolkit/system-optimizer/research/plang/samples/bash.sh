#!/usr/bin/env bash
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
for i in 0 1 2 3; do echo $((i*i)) & done | sort -n | tr '\n' ',' | sed 's/,$//' > /tmp/plang_bg.txt
echo "CONCURRENCY=$(cat /tmp/plang_bg.txt)"
rm -f /tmp/plang_bg.txt
