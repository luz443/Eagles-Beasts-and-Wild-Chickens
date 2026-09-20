/**
 * 两端契约一致性测试。
 *
 * 背景：浏览器侧 ContractValidator 是 Python Validator 的镜像实现。
 * 只测 Python 一侧无法防住漂移——必须让同一批夹具同时过两套实现，并逐条比对结论。
 * 运行：node web/tests/contract-parity.mjs   （退出码非 0 即不一致）
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { ContractValidator, DIMS } from "../js/contracts.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..", "..");
const expected = JSON.parse(fs.readFileSync(path.join(root, "reports", "contract-parity.json"), "utf8"));
const v = new ContractValidator();

const problems = [];

// 1. 维度枚举
if (JSON.stringify(DIMS) !== JSON.stringify(expected.dims)) {
  problems.push("DIMS 与 Python 侧不一致：\n  js=" + JSON.stringify(DIMS)
    + "\n  py=" + JSON.stringify(expected.dims));
}

// 2. 夹具：违规路径集合必须逐条相等
for (const [file, pyPaths] of Object.entries(expected.fixtures)) {
  const raw = JSON.parse(fs.readFileSync(path.join(root, "contracts", "fixtures", file), "utf8"));
  const jsPaths = v.validateArchive(raw).map(x => x.path).sort();
  const pySorted = pyPaths.slice().sort();
  if (JSON.stringify(jsPaths) !== JSON.stringify(pySorted)) {
    problems.push(`夹具 ${file} 结论不一致：\n  js=${JSON.stringify(jsPaths)}\n  py=${JSON.stringify(pySorted)}`);
  }
}

// 3. 去重指纹：与 Python 侧对同一输入必须给出同一个键
for (const { input, key } of expected.dedup_samples) {
  const jsKey = v.dedupKeyForParity(input);
  if (jsKey !== key) {
    problems.push("去重指纹不一致：\n  js=" + JSON.stringify(jsKey) + "\n  py=" + JSON.stringify(key));
  }
}

// 4. 畸形输入不得把校验器打崩
const hostile = [null, "x", 42, [], { records: [null] }];
for (const h of hostile) {
  try {
    v.validateLibrary(h);
    v.validateArchive(h);
  } catch (e) {
    problems.push("校验器在畸形输入上抛异常（应返回违规列表）：" + JSON.stringify(h) + " -> " + e.message);
  }
}

if (problems.length) {
  console.error("两端一致性测试失败（" + problems.length + " 项）：");
  for (const p of problems) console.error(" - " + p);
  process.exit(1);
}
console.log("两端一致性测试通过："
  + Object.keys(expected.fixtures).length + " 个夹具 + "
  + expected.dedup_samples.length + " 个指纹样本 + 维度枚举，结论逐条相等。");
