"""novelist 用 YAML ローダ。

PyYAML が入っていればそれを使う。無ければ、novelist のテンプレートが使う
YAML サブセット(マップ / リスト / インラインリスト / `|` ブロックスカラー /
コメント)だけを読む簡易パーサにフォールバックする。

環境変数 NOVELIST_NO_PYYAML=1 でフォールバックを強制できる(テスト用)。
"""

import os
import re


class ParseError(Exception):
    pass


def load_yaml(path):
    """ファイルを読んで dict / list / scalar を返す。"""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if os.environ.get("NOVELIST_NO_PYYAML") != "1":
        try:
            import yaml  # type: ignore
            return yaml.safe_load(text)
        except ImportError:
            pass
    return loads(text)


def loads(text):
    return _Parser(text).parse()


def _strip_comment(s):
    out = []
    q = None
    for i, ch in enumerate(s):
        if q:
            out.append(ch)
            if ch == q:
                q = None
        else:
            if ch in "\"'":
                q = ch
                out.append(ch)
            elif ch == "#" and (i == 0 or s[i - 1] in " \t"):
                break
            else:
                out.append(ch)
    return "".join(out).strip()


def _split_top(s):
    """インラインリストの中身をクォートを尊重してカンマ分割する。"""
    parts = []
    buf = []
    q = None
    for ch in s:
        if q:
            buf.append(ch)
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
            buf.append(ch)
        elif ch == ",":
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts


def _scalar(s):
    s = s.strip()
    if s in ("", "null", "~"):
        return None
    if s == "true":
        return True
    if s == "false":
        return False
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [_scalar(x) for x in _split_top(inner)]
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


_KEY_RE = re.compile(r"^[^:\[\]{}]+:(\s|$)")


class _Parser:
    def __init__(self, text):
        self.raw = text.splitlines()
        self.pos = 0

    def parse(self):
        result = self._block(0)
        return result

    # --- 低レベル ---

    def _peek(self):
        """次の意味のある行を返す(空行・コメント行はスキップ)。"""
        while self.pos < len(self.raw):
            line = self.raw[self.pos]
            s = line.strip()
            if s == "" or s.startswith("#"):
                self.pos += 1
                continue
            return line
        return None

    @staticmethod
    def _indent(line):
        return len(line) - len(line.lstrip(" "))

    # --- 構造 ---

    def _block(self, min_indent):
        line = self._peek()
        if line is None:
            return None
        cur = self._indent(line)
        if cur < min_indent:
            return None
        if line.strip().startswith("- "):
            return self._list(cur)
        return self._map(cur)

    def _map(self, indent):
        m = {}
        while True:
            line = self._peek()
            if line is None:
                break
            cur = self._indent(line)
            if cur < indent:
                break
            if cur > indent:
                raise ParseError(
                    "L%d: 予期しないインデント: %r" % (self.pos + 1, line)
                )
            s = line.strip()
            if s.startswith("- "):
                break
            if ":" not in s:
                raise ParseError("L%d: `key: value` 形式でない行: %r" % (self.pos + 1, line))
            key, _, rest = s.partition(":")
            key = key.strip().strip("\"'")
            rest = _strip_comment(rest.strip())
            self.pos += 1
            if rest in ("|", "|-", "|+"):
                m[key] = self._literal(indent, chomp=rest)
            elif rest == "":
                child = self._block(indent + 1)
                if child is None:
                    # 「キーと同じインデントのリスト」(YAMLでは合法)を救済する
                    nxt = self._peek()
                    if (
                        nxt is not None
                        and self._indent(nxt) == indent
                        and nxt.strip().startswith("- ")
                    ):
                        child = self._list(indent)
                m[key] = child
            else:
                m[key] = _scalar(rest)
        return m

    def _list(self, indent):
        out = []
        while True:
            line = self._peek()
            if line is None:
                break
            if self._indent(line) != indent or not line.strip().startswith("- "):
                break
            s = _strip_comment(line.strip()[2:])
            if s == "":
                self.pos += 1
                out.append(self._block(indent + 1))
            elif _KEY_RE.match(s):
                # dict 項目: 行を仮想的に書き換えて map として読む
                self.raw[self.pos] = " " * (indent + 2) + s
                out.append(self._map(indent + 2))
            else:
                self.pos += 1
                out.append(_scalar(s))
        return out

    def _literal(self, parent_indent, chomp="|"):
        buf = []
        while self.pos < len(self.raw):
            line = self.raw[self.pos]
            if line.strip() == "":
                buf.append("")
                self.pos += 1
                continue
            if self._indent(line) <= parent_indent:
                break
            buf.append(line)
            self.pos += 1
        while buf and buf[-1] == "":
            buf.pop()
        if not buf:
            return ""
        base = min(self._indent(l) for l in buf if l.strip())
        body = "\n".join((l[base:] if l.strip() else "") for l in buf)
        return body if chomp == "|-" else body + "\n"
