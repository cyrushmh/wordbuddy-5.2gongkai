/* ================= 引擎（node 验证同款） ================= */
const amp=c=>Math.hypot(c[0],c[1]);                       // 复数模长
const cmul=(a,b)=>[a[0]*b[0]-a[1]*b[1], a[0]*b[1]+a[1]*b[0]];
const matVec=(M,v)=>M.map(r=>r.reduce((ac,x,j)=>[ac[0]+cmul(x,v[j])[0],ac[1]+cmul(x,v[j])[1]],[0,0]));
const fullGate=(U,n,q)=>{const N=1<<n;
  return Array.from({length:N},(_,s)=>Array.from({length:N},(_,t)=>
    ((s&~(1<<q))===(t&~(1<<q)))?U[(s>>q)&1][(t>>q)&1]:[0,0]));};
const permGate=(n,f)=>{const N=1<<n;
  const M=Array.from({length:N},()=>Array.from({length:N},()=>[0,0]));
  for(let s=0;s<N;s++)M[f(s)][s]=[1,0];   // 规范方向 |s> → |f(s)>
  return M;};
const CNOT=(n,c,t)=>permGate(n,s=>((s>>c)&1)?s^(1<<t):s);
const SWAPM=(n,a,b)=>permGate(n,s=>{const ba=(s>>a)&1,bb=(s>>b)&1;
  return ba===bb?s:(s^(1<<a)^(1<<b));});
const QFT=(n)=>{const N=1<<n,w=2*Math.PI/N;
  return Array.from({length:N},(_,j)=>Array.from({length:N},(_,k)=>
    [Math.cos(w*j*k)/Math.sqrt(N),Math.sin(w*j*k)/Math.sqrt(N)]));};
const QFTdag=(n)=>{const Q=QFT(n);
  return Q.map((row,j)=>row.map((c,k)=>[Q[k][j][0],-Q[k][j][1]]));};
// Born 采样：单比特 Z 测量。r∈[0,1) 为均匀随机源（可注入以便测试）。
// 测量前相位连续 = 过渡态「无」；测量后其余基态振幅归零（离散化）。
const measureQ=(v,q,r)=>{const p=[0,0];
  for(let i=0;i<v.length;i++){const A=amp(v[i]);p[(i>>q)&1]+=A*A;}
  const tot=p[0]+p[1]; if(tot<=0)return{b:0,state:v};
  const b=r<p[0]/tot?0:1;
  const w=v.map((c,i)=>((i>>q)&1)===b?c:[0,0]);
  const n2=Math.sqrt(w.reduce((s,c)=>s+amp(c)*amp(c),0));
  return{b,state:w.map(c=>[c[0]/n2,c[1]/n2])};};
const U2={
  H:[[[.70710678,0],[.70710678,0]],[[.70710678,0],[-.70710678,0]]],
  X:[[[0,0],[1,0]],[[1,0],[0,0]]],
  Y:[[[0,0],[0,-1]],[[0,1],[0,0]]],
  Z:[[[1,0],[0,0]],[[0,0],[-1,0]]],
  S:[[[1,0],[0,0]],[[0,0],[0,1]]],
  T:[[[1,0],[0,0]],[[0,0],[.70710678,.70710678]]],
};
// 相变矩阵（数字转换逻辑门）：P(θ)=diag(1, e^{iθ})。θ=π/2 即 S、π 即 Z、3π/2 即 S†。
// 六比特各配一枚：步进 90°（二值+过渡：正/负/±i）或 120°（三相：0/120/240）。
const phaseGate=(n,q,th)=>fullGate([[[1,0],[0,0]],[[0,0],[Math.cos(th),Math.sin(th)]]],n,q);
// 数制转换：6 位 = 3 对 qubit；每对是 1 个三进制位（trit）。00→0 / 01→1 / 10→2 / 11→无效码。
const PAIR2T=[0,1,2,null];
const TRIT2PAIR=[0,1,2];
const bitsToTrits=b=>{const t=[];for(let p=0;p<3;p++)
  t.push(PAIR2T[((b>>(2*p))&1)|(((b>>(2*p+1))&1)<<1)]);return t;};
const tritsToBits=t=>{let b=0;for(let p=0;p<3;p++)b|=TRIT2PAIR[t[p]&3]<<(2*p);return b;};
const packTrit5=t=>t[0]+t[1]*3+t[2]*9;            // 3 trit（0..26）→ 传统二进制 5 bit
const pack5ToBin=v=>v.toString(2).padStart(5,"0");
// 三进制寄存器：3 个 trit 等幅叠加（1/√27），余 37 个基态为缺失态（可作校验位）
const tritRegister=()=>{const v=Array.from({length:64},()=>[0,0]),a=1/Math.sqrt(27);
  for(let x=0;x<3;x++)for(let y=0;y<3;y++)for(let z=0;z<3;z++)
    v[tritsToBits([x,y,z])]=[a,0];return v;};

export {amp, matVec, fullGate, permGate, CNOT, SWAPM, QFT, QFTdag, phaseGate, measureQ, bitsToTrits, tritsToBits, packTrit5, pack5ToBin, tritRegister, TRIT2PAIR, U2};
