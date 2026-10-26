// WASM 端到端验证（Node，无需 wasmtime）：
// 通过导出的 CLASSICS_INBUF/OUTBUF 内存区把字节送入内核，再读回解码结果。
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const wasmPath = join(__dirname, '..', 'dist', 'classics-wasm32-unknown-unknown.wasm');
const bytes = readFileSync(wasmPath);

const { instance } = await WebAssembly.instantiate(bytes, {});
const ex = instance.exports;

const mem = () => ex.memory.buffer;
const inPtr = ex.classics_inbuf_ptr();
const outPtr = ex.classics_outbuf_ptr();
const ver = ex.classics_version();
const verStr = new TextDecoder().decode(new Uint8Array(mem(), ver, 32).subarray(0, 32)).replace(/\0.*/, '');

console.log('classics_version() =>', verStr);

function decodeBytes(inputBytes) {
  const m = mem();
  new Uint8Array(m, inPtr, inputBytes.length).set(inputBytes);
  const n = ex.classics_decode_inbuf(inputBytes.length);
  return new TextDecoder('utf-8').decode(new Uint8Array(m, outPtr, n));
}

let pass = 0, fail = 0;
function check(name, got, want) {
  if (got === want) { pass++; console.log(`  PASS ${name}`); }
  else { fail++; console.log(`  FAIL ${name}: got=${JSON.stringify(got)} want=${JSON.stringify(want)}`); }
}

// 1) UTF-8 透传
check('utf8 中文测试', decodeBytes(new TextEncoder().encode('中文测试——道德经')), '中文测试——道德经');

// 2) GB18030 回退："中" 的 GB18030 编码为 0xD6 0xD0，"国" 为 0xB9 0xFA
check('gb18030 中国', decodeBytes(new Uint8Array([0xD6, 0xD0, 0xB9, 0xFA])), '中国');

// 3) 非法字节 -> 损失性替换（含 U+FFFD）
const lossy = decodeBytes(new Uint8Array([0xFF, 0xFE, 0x41, 0x42]));
check('lossy 含 U+FFFD', lossy.includes('�'), true);

console.log(`\nWASM 验证：${pass} 通过 / ${fail} 失败`);
process.exit(fail === 0 ? 0 : 1);
