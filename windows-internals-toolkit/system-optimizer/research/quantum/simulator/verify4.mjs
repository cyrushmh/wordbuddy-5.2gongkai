import {matVec, fullGate, CNOT, measureQ, U2} from './html_engine.mjs';
const zero=n=>{const v=Array.from({length:1<<n},()=>[0,0]);v[0]=[1,0];return v;};
const ok=(name,got,exp,tol=0.002)=>{
  const err=got.map((c,i)=>Math.max(Math.abs(c[0]-exp[i][0]),Math.abs(c[1]-exp[i][1]))).reduce((a,b)=>Math.max(a,b),0);
  console.log((err<tol?"✓":"✗")+` ${name}  最大误差 ${err.toExponential(2)}`);
  if(err>=tol)process.exitCode=1;};
// 阴阳对缠：天罡（气液固 q5q4q3）× 地煞（波磁电 q2q1q0）互补纠缠
// |罡000·煞111> + |罡111·煞000> = |000111> + |111000>（互根，非乘积）
const yy=zero(6);yy[0]=[0,0];yy[7]=[0.70710678,0];yy[56]=[0.70710678,0];
const expYY=new Array(64).fill(0).map(()=>[0,0]);
expYY[7]=[0.7071,0];expYY[56]=[0.7071,0];
ok("阴阳对缠（罡0煞1/罡1煞0）",yy,expYY);
// 阴阳一体：六位同 0 或同 1（GHZ6，两卦之差 = 63 即每一位对偶）
let g6=zero(6);g6=matVec(fullGate(U2.H,6,5),g6);
for(let q=5;q>0;q--)g6=matVec(CNOT(6,q,q-1),g6);
const expG6=new Array(64).fill(0).map(()=>[0,0]);
expG6[0]=[0.7071,0];expG6[63]=[0.7071,0];
ok("阴阳一体 GHZ6",g6,expG6);
// measureQ 确定性：Bell 态单比特 Z 测量，其余基态归零
const bell=matVec(CNOT(2,0,1),matVec(fullGate(U2.H,2,0),zero(2)));
const m0=measureQ(bell,0,0.3);
ok("观测 Bell q0 (r=0.3) → b=0",m0.state,[[1,0],[0,0],[0,0],[0,0]]);
console.log((m0.b===0?"✓":"✗")+" 测得 b=0（相位连续性被打断）");
if(m0.b!==0)process.exitCode=1;
const m1=measureQ(bell,0,0.7);
ok("观测 Bell q0 (r=0.7) → b=1",m1.state,[[0,0],[0,0],[0,0],[1,0]]);
console.log((m1.b===1?"✓":"✗")+" 测得 b=1（另一分位随之定值）");
if(m1.b!==1)process.exitCode=1;
// Born 频率统计：10000 次均匀随机源 → p(0)=1/2
let c0=0;for(let t=0;t<10000;t++)if(measureQ(bell,0,t/10000).b===0)c0++;
const freq=c0/10000;
console.log((Math.abs(freq-0.5)<0.02?"✓":"✗")+` Born 采样频率 p(0)=${freq.toFixed(4)}（期望 0.5000）`);
if(Math.abs(freq-0.5)>=0.02)process.exitCode=1;
