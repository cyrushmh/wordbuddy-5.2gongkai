import {matVec, fullGate, phaseGate, bitsToTrits, tritsToBits, packTrit5, pack5ToBin, tritRegister, TRIT2PAIR, amp} from './html_engine.mjs';
const zero=n=>{const v=Array.from({length:1<<n},()=>[0,0]);v[0]=[1,0];return v;};
const ok=(name,got,exp,tol=0.002)=>{
  const err=got.map((c,i)=>Math.max(Math.abs(c[0]-exp[i][0]),Math.abs(c[1]-exp[i][1]))).reduce((a,b)=>Math.max(a,b),0);
  console.log((err<tol?"✓":"✗")+` ${name}  最大误差 ${err.toExponential(2)}`);
  if(err>=tol)process.exitCode=1;};
// 相变矩阵 P(θ)=diag(1,e^{iθ})：θ=π/2 即 S、π 即 Z、3π/2 即 S†
const one01=[[0,0],[1,0],[0,0],[0,0]];   // |01>
ok("相变 P(90°)|01>=i|01>",matVec(phaseGate(2,0,Math.PI/2),one01),[[0,0],[0,1],[0,0],[0,0]]);
ok("相变 P(180°)|01>=-|01>",matVec(phaseGate(2,0,Math.PI),one01),[[0,0],[-1,0],[0,0],[0,0]]);
ok("相变 P(270°)|01>=-i|01>",matVec(phaseGate(2,0,Math.PI*1.5),one01),[[0,0],[0,-1],[0,0],[0,0]]);
// 数制映射往返：3 trit ↔ 6 位（成对码），27 个合法组合逐一验证
let rt=0;
for(let x=0;x<3;x++)for(let y=0;y<3;y++)for(let z=0;z<3;z++){
  const t=[x,y,z],b=tritsToBits(t),back=bitsToTrits(b);
  if(b>=0&&b<64&&back[0]===x&&back[1]===y&&back[2]===z)rt++;}
console.log((rt===27?"✓":"✗")+` trit↔bit 往返 27/27`);
if(rt!==27)process.exitCode=1;
// 无效对：11 → null
console.log((bitsToTrits(0b000011)[0]===null?"✓":"✗")+" 无效对 11 检出（trit0=null）");
if(bitsToTrits(0b000011)[0]!==null)process.exitCode=1;
// 3 trit → 5 bit 紧 pack：26 = 11010
console.log((packTrit5([2,2,2])===26&&pack5ToBin(26)==="11010"?"✓":"✗")+" 3 trit=26 → 5 bit 11010");
if(packTrit5([2,2,2])!==26||pack5ToBin(26)!=="11010")process.exitCode=1;
// 三进制寄存器：27 项等幅 1/√27，其余 37 项为缺失态
const tr=tritRegister(),a=1/Math.sqrt(27);
let nz=0,err=0;
tr.forEach(c=>{if(amp(c)>1e-9){nz++;err=Math.max(err,Math.abs(amp(c)-a));}});
console.log((nz===27&&err<0.001?"✓":"✗")+` 三进制寄存器：27 项等幅 1/√27（误差 ${err.toExponential(1)}），余 ${64-nz} 项缺失`);
if(nz!==27||err>=0.001)process.exitCode=1;
