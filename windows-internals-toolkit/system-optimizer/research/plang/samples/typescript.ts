const x: number = 42, s: string = "hi", b: boolean = true, n: null = null;
console.log("LANG=TypeScript");
console.log(`LITERALS=${x},${s},${b},${n}`);
console.log(`OPS=${(7*6)+"abc".length}`);
let acc = 0; for (let i = 1; i < 6; i++) acc += i;
console.log(`CONTROL=${acc}`);
const fact = (k: number): number => k <= 1 ? 1 : k * fact(k-1);
console.log(`FUNC=${fact(5)}`);
const arr: number[] = [1,2,3], d: Record<string, number> = {a: 1};
console.log(`DATA=${arr.length},${d.a}`);
const p = Deno.makeTempFileSync(); Deno.writeTextFileSync(p, "io"); Deno.readTextFileSync(p); Deno.removeSync(p);
console.log("IO=ok");
try { JSON.parse("{bad"); } catch (e) { console.log(`ERROR=${(e as Error).constructor.name}`); }
const r = await Promise.all([0,1,2,3].map(i => Promise.resolve(i*i)));
console.log(`CONCURRENCY=${JSON.stringify(r)}`);
