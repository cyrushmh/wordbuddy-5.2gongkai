console.log("LANG=JavaScript");
const x=42, s="hi", b=true, n=null;
console.log(`LITERALS=${x},${s},${b},${n}`);
console.log(`OPS=${(7*6)+"abc".length}`);
let acc=0; for(let i=1;i<6;i++) acc+=i;
console.log(`CONTROL=${acc}`);
const fact=k=>k<=1?1:k*fact(k-1);
console.log(`FUNC=${fact(5)}`);
const arr=[1,2,3], d={a:1};
console.log(`DATA=${arr.length},${d.a}`);
const fs=require("fs"), os=require("os"), path=require("path");
const p=path.join(os.tmpdir(),"plang_js.txt"); fs.writeFileSync(p,"io"); fs.readFileSync(p); fs.unlinkSync(p);
console.log("IO=ok");
try { 0/0; throw new Error("x"); } catch(e){}
try { JSON.parse("{bad"); } catch(e){ console.log(`ERROR=${e.constructor.name}`); }
(async()=>{ const r=await Promise.all([0,1,2,3].map(i=>Promise.resolve(i*i)));
  console.log(`CONCURRENCY=${JSON.stringify(r)}`); })();
