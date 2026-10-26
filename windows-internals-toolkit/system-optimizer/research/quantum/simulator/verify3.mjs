import {matVec, fullGate, permGate, CNOT, SWAPM, QFT, QFTdag, U2} from './html_engine.mjs';
const zero=n=>{const v=Array.from({length:1<<n},()=>[0,0]);v[0]=[1,0];return v;};
const ok=(name,got,exp,tol=0.002)=>{
  const err=got.map((c,i)=>Math.max(Math.abs(c[0]-exp[i][0]),Math.abs(c[1]-exp[i][1]))).reduce((a,b)=>Math.max(a,b),0);
  console.log((err<tol?"✓":"✗")+` ${name}  最大误差 ${err.toExponential(2)}`);
  if(err>=tol)process.exitCode=1;};
// H(0)|00>
ok("H(0)|00>",matVec(fullGate(U2.H,2,0),zero(2)),
   [[0.7071,0],[0.7071,0],[0,0],[0,0]]);
// X（小端序：显示 01 = q1=0,q0=1；X 翻 q0 → 00）
ok("X(0)|01>→|00>",matVec(fullGate(U2.X,2,0),[[0,0],[1,0],[0,0],[0,0]]),[[1,0],[0,0],[0,0],[0,0]]);
// Y：Y|0>=i|1>，Y|1>=-i|0>（对角恒为零）
ok("Y(0)|00>→i|01>",matVec(fullGate(U2.Y,2,0),zero(2)),[[0,0],[0,1],[0,0],[0,0]]);
ok("Y(0)|01>→-i|00>",matVec(fullGate(U2.Y,2,0),[[0,0],[1,0],[0,0],[0,0]]),[[0,-1],[0,0],[0,0],[0,0]]);
// Z
ok("Z(0)半叠加",matVec(fullGate(U2.Z,2,0),[[0.7071,0],[0.7071,0],[0,0],[0,0]]),[[0.7071,0],[-0.7071,0],[0,0],[0,0]]);
// S
ok("S(0)|0>+i|1>",matVec(fullGate(U2.S,2,0),[[0.7071,0],[0.7071,0],[0,0],[0,0]]),[[0.7071,0],[0,0.7071],[0,0],[0,0]]);
// T
ok("T(0)",matVec(fullGate(U2.T,2,0),[[0.7071,0],[0.7071,0],[0,0],[0,0]]),
   [[0.7071,0],[0.5,0.5],[0,0],[0,0]]);
// 置换门规范方向：|s> → |f(s)>（用非对合循环 s→s+1 验证，对合置换查不出方向错）
ok("permGate 循环 |00>→|01>",matVec(permGate(2,s=>(s+1)&3),zero(2)),[[0,0],[1,0],[0,0],[0,0]]);
// Bell
const bell=matVec(CNOT(2,0,1),matVec(fullGate(U2.H,2,0),zero(2)));
ok("Bell",bell,[[0.7071,0],[0,0],[0,0],[0.7071,0]]);
// SWAP
ok("SWAP|10>=|01>",matVec(SWAPM(2,0,1),(()=>{const v=zero(2);v[0]=[0,0];v[2]=[1,0];return v;})()),
   [[0,0],[1,0],[0,0],[0,0]]);
// QFT(Bell)
ok("QFT(Bell)",matVec(QFT(2),bell),[[0.7071,0],[0.3536,-0.3536],[0,0],[0.3536,0.3536]]);
// QFT† 是 QFT 的逆：QFT†·QFT = I
const uni3=matVec(fullGate(U2.H,3,2),matVec(fullGate(U2.H,3,1),matVec(fullGate(U2.H,3,0),zero(3))));
const f=matVec(QFT(3),uni3);
const back=matVec(QFTdag(3),f);
ok("QFT†(QFT(均匀))=均匀",back,new Array(8).fill(0).map((_,i)=>[0.3536,0]));
// 均匀叠加（页面 preset('uniform') 同款全 H 链）
ok("均匀叠加(3b)",uni3,new Array(8).fill(0).map(()=>[0.3536,0]));
// 3-bit GHZ（页面 preset('ghz') 同款：H(q2) → CNOT 2→1 → CNOT 1→0）
const g3=matVec(CNOT(3,1,0),matVec(CNOT(3,2,1),matVec(fullGate(U2.H,3,2),zero(3))));
ok("GHZ3",g3,[[0.7071,0],[0,0],[0,0],[0,0],[0,0],[0,0],[0,0],[0.7071,0]]);
ok("QFT(GHZ3) 第4频缺失",matVec(QFT(3),g3),
   [[0.5,0],[0.4268,-0.1768],[0.25,-0.25],[0.0732,-0.1768],[0,0],[0.0732,0.1768],[0.25,0.25],[0.4268,0.1768]]);
ok("QFT(均匀)=零频单峰",matVec(QFT(3),uni3),
   [[1,0],[0,0],[0,0],[0,0],[0,0],[0,0],[0,0],[0,0]]);
