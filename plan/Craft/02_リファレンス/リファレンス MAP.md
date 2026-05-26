---
project: "Craft"
tags: [project, dev, satellite, reference-map]
---

# リファレンス MAP

> 親: [[Craft]]

`02_リファレンス/` は **外部仕様の抜粋** と **早見表**。書くときに横に置く資料。

---

| ノート | 用途 | いつ見るか |
|---|---|---|
| [[veriq仕様メモ]] | veriq 公式ドキュメントから抽出した CLI / Python API リファレンス | `vq.Ref` / `vq.Table` / `vq.Scope` の正確な signature を確認したい時、veriq の関数を呼ぶ時 |
| [[宣言とTOMLの対応表]] | 全 9 パターンの Python 宣言 ⇔ TOML 早見表 | `class X(Component):` (P1 default Singleton) と `class X(Component, MultiInstance):` (P3) が TOML でどう見えるか、`shared_spec=True/False` の差を確認したい時 |

## 関連する一次資料

- veriq 公式: https://www.space.t.u-tokyo.ac.jp/veriq/
- Pydantic v2 docs: https://docs.pydantic.dev/
- TOML spec: https://toml.io/
