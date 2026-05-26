# セキュリティ

エージェントが守るべきセキュリティ規約。詳細は [`RULES.md`](../../RULES.md) も参照。

## コミット前チェック（必須）

- [ ] ハードコードされたシークレット（API キー・パスワード・トークン）がない
- [ ] ユーザー入力をすべて検証している
- [ ] SQL インジェクション対策（parameterized query）
- [ ] XSS 対策（HTML サニタイズ）
- [ ] CSRF 対策が有効
- [ ] 認証・認可を確認
- [ ] レート制限がある
- [ ] エラーメッセージにシークレットや内部情報を含めない

## シークレット管理

- ソースコードに直接書かない
- 環境変数またはシークレットマネージャを使う
- 起動時に必須シークレットの存在を検証
- 漏洩が疑われたら即座にローテーション

## セッション永続化

- `session_start.py` / `session_end.py` / `pre_compact.py` は `CLAUDE_SESSION_PERSIST=1` の時だけ動作する
- 有効化すると `.claude/sessions/` に会話由来の要約が保存されるため、機密プロジェクトでは必要性を確認してから使う
- 保存前にメールアドレス、トークン風文字列、`/Users/<name>` は redaction されるが、完全な DLP ではない
- `.claude/sessions/` は git 管理に含めない

## セキュリティイベント対応

問題発見時の手順:

1. **STOP** — それ以上の変更を止める
2. `/security-review` スキルまたは security-reviewer エージェントを起動
3. CRITICAL を最初に修正
4. 漏洩シークレットがあればローテーション
5. 同種の問題が他にないか全体スキャン

## 外部ツール

### AgentShield

エージェントが生成・実行するコードに対する脆弱性スキャナ（ECC エコシステム発・npm 配布）。

- パッケージ: [`ecc-agentshield`](https://www.npmjs.com/package/ecc-agentshield)
- 用途: プロンプトインジェクション、シェル注入、機密ファイルアクセス等の検出
- 導入は任意。CI でエージェント生成コードを通すと効果が高い

```bash
npx ecc-agentshield scan <path>
```

### その他

- [Semgrep](https://semgrep.dev/) — 多言語静的解析
- [Trivy](https://trivy.dev/) — 依存脆弱性スキャン
- [gitleaks](https://github.com/gitleaks/gitleaks) — シークレット検出

これらは `pre-commit` または CI に組み込むと自動化できる。
