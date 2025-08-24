from pathlib import Path
import re
import sys
from typing import List, Set, Optional

from utils.logger_helper import setup_logger

logger = setup_logger()

# 常见的二进制文件扩展名和大文件阈值
BINARY_EXTENSIONS = {".exe", ".bin", ".so", ".dll", ".dylib", ".o", ".a", ".lib"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
MAX_DEPTH = 50  # 最大递归深度


class GitignoreParser:
    """高效的gitignore解析器"""

    def __init__(self):
        self.patterns = []
        self.dir_patterns = []
        self.negation_patterns = []

    def parse_gitignore(self, gitignore_path: Path) -> None:
        """解析gitignore文件"""
        if not gitignore_path.exists():
            return

        try:
            # 尝试多种编码
            for encoding in ["utf-8", "gbk", "latin-1"]:
                try:
                    with open(gitignore_path, "r", encoding=encoding) as f:
                        self._parse_lines(f.readlines())
                    break
                except UnicodeDecodeError:
                    continue
            else:
                logger.warning("无法读取gitignore文件: %s", gitignore_path)
        except (OSError, IOError) as e:
            logger.warning("读取gitignore文件失败: %s, 错误: %s", gitignore_path, e)

    def _parse_lines(self, lines: List[str]) -> None:
        """解析gitignore行"""
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # 处理否定模式
            is_negation = line.startswith("!")
            if is_negation:
                line = line[1:]

            # 处理目录模式
            is_dir_only = line.endswith("/")
            if is_dir_only:
                line = line[:-1]

            # 转换为正则表达式
            pattern = self._gitignore_to_regex(line)

            if is_negation:
                self.negation_patterns.append((pattern, is_dir_only))
            elif is_dir_only:
                self.dir_patterns.append(pattern)
            else:
                self.patterns.append(pattern)

    def _gitignore_to_regex(self, pattern: str) -> re.Pattern:
        """将gitignore模式转换为正则表达式"""
        # 转义特殊字符
        pattern = re.escape(pattern)

        # 恢复gitignore通配符
        pattern = pattern.replace(r"\*\*", ".*")  # **匹配任意路径
        pattern = pattern.replace(r"\*", "[^/]*")  # *匹配除/外的任意字符
        pattern = pattern.replace(r"\?", "[^/]")  # ?匹配单个字符

        # 处理路径匹配
        if not pattern.startswith(".*") and not pattern.startswith("/"):
            pattern = f"(^|/)({pattern})"
        elif pattern.startswith("/"):
            pattern = f"^{pattern[1:]}"

        try:
            return re.compile(pattern)
        except re.error as e:
            logger.warning("无效的gitignore模式: %s, 错误: %s", pattern, e)
            return re.compile(re.escape(pattern))

    def should_ignore(self, path_str: str, is_dir: bool = False) -> bool:
        """检查路径是否应该被忽略"""
        # 检查普通模式
        for pattern in self.patterns:
            if pattern.search(path_str):
                # 检查是否有否定模式覆盖
                for neg_pattern, neg_dir_only in self.negation_patterns:
                    if (not neg_dir_only or is_dir) and neg_pattern.search(path_str):
                        return False
                return True

        # 检查目录专用模式
        if is_dir:
            for pattern in self.dir_patterns:
                if pattern.search(path_str):
                    for neg_pattern, _ in self.negation_patterns:
                        if neg_pattern.search(path_str):
                            return False
                    return True

        return False


def is_safe_path(path: Path, base_path: Path) -> bool:
    """检查路径是否安全"""
    try:
        path.resolve().relative_to(base_path.resolve())
        return True
    except (ValueError, OSError):
        return False


def should_skip_file(path: Path) -> bool:
    """检查是否应该跳过文件"""
    try:
        # 检查文件大小
        if path.stat().st_size > MAX_FILE_SIZE:
            return True

        # 检查二进制文件
        if path.suffix.lower() in BINARY_EXTENSIONS:
            return True

        return False
    except (OSError, IOError):
        return True


def get_tree_pathlib(
    path: str = ".",
    indent: str = "",
    gitignore_parser: Optional[GitignoreParser] = None,
    base_path: Optional[Path] = None,
    visited: Optional[Set[Path]] = None,
    depth: int = 0,
    max_depth: int = MAX_DEPTH,
) -> str:
    """
    获得目录树结构

    Args:
        path: 要遍历的路径
        indent: 缩进字符串
        gitignore_parser: gitignore解析器
        base_path: 基础路径
        visited: 已访问路径集合（防止循环）
        depth: 当前深度
        max_depth: 最大深度
    Returns:
        目录树字符串
    """
    # 深度限制
    if depth > max_depth:
        return f"{indent}... (超过最大深度 {max_depth})\n"

    try:
        current_path = Path(path).resolve()
    except (OSError, IOError) as e:
        logger.warning("无法解析路径: %s, 错误: %s", path, e)
        return ""

    # 初始化
    if base_path is None:
        base_path = current_path
        visited = set()
        gitignore_parser = GitignoreParser()
        # 解析根目录的gitignore
        gitignore_parser.parse_gitignore(base_path / ".gitignore")

    # 安全检查
    if not is_safe_path(current_path, base_path):
        logger.warning("不安全的路径: %s", current_path)
        return ""

    # 防止循环引用
    if current_path in visited:
        return f"{indent}🔄 {current_path.name} (循环引用)\n"
    visited.add(current_path)

    result = ""

    try:
        # 解析当前目录的gitignore
        if current_path != base_path:
            local_gitignore = current_path / ".gitignore"
            if local_gitignore.exists():
                local_parser = GitignoreParser()
                local_parser.parse_gitignore(local_gitignore)
                # 这里可以考虑合并解析器，为简化直接使用全局解析器

        items = []
        for item in current_path.iterdir():
            # 安全检查
            if not is_safe_path(item, base_path):
                continue

            # 计算相对路径用于gitignore检查
            try:
                relative_path = item.relative_to(base_path)
                path_str = str(relative_path).replace("\\", "/")
            except ValueError:
                continue

            # 检查gitignore
            if gitignore_parser and gitignore_parser.should_ignore(
                path_str, item.is_dir()
            ):
                continue

            # 检查是否应该跳过
            if item.is_file() and should_skip_file(item):
                continue

            items.append(item)

        # 排序：目录优先，然后按名称
        items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))

        # 遍历项目
        for i, item in enumerate(items):
            is_last = i == len(items) - 1

            if item.is_dir():
                result += f"{indent}{'└── ' if is_last else '├── '}📁 {item.name}/\n"
                next_indent = indent + ("    " if is_last else "│   ")
                result += get_tree_pathlib(
                    str(item),
                    next_indent,
                    gitignore_parser,
                    base_path,
                    visited,
                    depth + 1,
                    max_depth,
                )
            elif item.is_file():
                # 文件大小信息
                try:
                    size = item.stat().st_size
                    if size > 1024 * 1024:
                        size_str = f" ({size // (1024*1024)}MB)"
                    elif size > 1024:
                        size_str = f" ({size // 1024}KB)"
                    else:
                        size_str = f" ({size}B)" if size > 0 else ""
                except OSError:
                    size_str = ""

                result += (
                    f"{indent}{'└── ' if is_last else '├── '}📄 {item.name}{size_str}\n"
                )
            elif item.is_symlink():
                try:
                    target = item.readlink()
                    result += f"{indent}{'└── ' if is_last else '├── '}🔗 {item.name} -> {target}\n"
                except OSError:
                    result += f"{indent}{'└── ' if is_last else '├── '}🔗 {item.name} -> (无法读取)\n"

    except PermissionError:
        result += f"{indent}❌ 权限拒绝\n"
    except OSError as e:
        logger.warning("访问目录失败: %s, 错误: %s", current_path, e)
        result += f"{indent}❌ 无法访问: {e}\n"
    finally:
        # 清理visited中的当前路径
        if current_path in visited:
            visited.discard(current_path)

    return result


def main():
    """主函数"""

    path = sys.argv[1] if len(sys.argv) > 1 else "."

    print(f"📂 目录树: {Path(path).resolve()}")
    print("=" * 50)

    try:
        print(get_tree_pathlib(path))
    except KeyboardInterrupt:
        print("\n\n操作已取消")
    except Exception as e:
        logger.error("程序执行错误: %s", e)
        print(f"❌ 执行失败: {e}")


if __name__ == "__main__":
    main()
