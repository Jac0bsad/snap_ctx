from typing import Dict, List, Optional, NamedTuple, Any
from pathlib import Path
import yaml


def init_config():
    """初始化配置，让用户添加模型配置和选择默认模型"""
    config_path = Path("config/models.yaml")

    # 确保配置目录存在
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # 如果配置文件不存在，从示例文件创建
    if not config_path.exists():
        example_path = Path("config/models.example.yaml")
        if example_path.exists():
            with open(example_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
        else:
            config_data = {"models": {}, "default_model": None}
    else:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

    print("=== 模型配置初始化 ===")

    # 添加新模型
    print("\n1. 添加新模型配置")
    while True:
        display_name = input("请输入模型显示名称 (直接回车结束添加): ").strip()
        if not display_name:
            break

        api_base = input("请输入API地址: ").strip()
        api_key = input("请输入API密钥: ").strip()
        model_name = input("请输入模型名称: ").strip()

        config_data["models"][display_name] = {
            "api_base": api_base,
            "api_key": api_key,
            "model_name": model_name,
        }
        print(f"✅ 已添加模型: {display_name}")

    # 选择默认模型
    print("\n2. 选择默认模型")
    available_models = list(config_data["models"].keys())
    if available_models:
        print("可用模型:")
        for i, model in enumerate(available_models, 1):
            print(f"  {i}. {model}")

        while True:
            try:
                choice = input(f"请选择默认模型 (1-{len(available_models)}): ").strip()
                if not choice:
                    break
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(available_models):
                    config_data["default_model"] = available_models[choice_idx]
                    print(f"✅ 已设置默认模型: {available_models[choice_idx]}")
                    break
                else:
                    print("❌ 无效的选择，请重新输入")
            except ValueError:
                print("❌ 请输入有效的数字")
    else:
        print("⚠️  没有可用的模型，请先添加模型")

    # 保存配置
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, allow_unicode=True, sort_keys=False)

    print(f"\n✅ 配置已保存到: {config_path}")
    print("=== 初始化完成 ===")


class LLMModelConfig(NamedTuple):
    """模型配置数据类"""

    api_base: str
    api_key: str
    model_name: str


class LLMConfigManager:
    """配置管理器，负责加载和管理模型配置"""

    def __init__(self, config_path: str = "config/models.yaml"):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径，相对于项目根目录
        """
        self.config_path = self._find_config_file(config_path)
        self._config_cache: dict = None
        self._load_config()

    def _find_config_file(self, config_path: str) -> Path:
        """查找配置文件的实际位置"""
        # 尝试多个可能的位置
        possible_paths = [
            Path(config_path),  # 相对于当前目录
            Path(__file__).parent / "models.yaml",  # 相对于此模块所在目录
            Path(__file__).parent.parent / config_path,  # 相对于项目根目录
            Path.cwd() / config_path,  # 相对于当前工作目录
        ]

        for path in possible_paths:
            if path.exists():
                return path

        # 如果都找不到，返回默认路径（会在_load_config中报错）
        return Path(config_path)

    def _load_config(self) -> None:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        try:
            with open(self.config_path, "r", encoding="utf-8") as file:
                self._config_cache = yaml.safe_load(file)
        except yaml.YAMLError as e:
            raise ValueError(f"配置文件格式错误: {e}") from e
        except Exception as e:
            raise RuntimeError(f"加载配置文件失败: {e}") from e

    def get_model_config(self, model_name: Optional[str] = None) -> LLMModelConfig:
        """
        获取指定模型的配置

        Args:
            model_name: 模型名称，如果为None则使用默认模型

        Returns:
            ModelConfig: 模型配置对象

        Raises:
            ValueError: 当模型不存在时
        """
        if model_name is None:
            model_name = self._config_cache.get("default_model", "deepseek")

        if "models" not in self._config_cache:
            raise ValueError("配置文件中未找到models配置")

        models = self._config_cache["models"]
        if model_name not in models:
            available_models = list(models.keys())
            raise ValueError(
                f"模型 '{model_name}' 不存在。可用模型: {available_models}"
            )

        model_config = models[model_name]

        # 验证必要字段
        required_fields = ["api_base", "api_key", "model_name"]
        for field in required_fields:
            if field not in model_config:
                raise ValueError(f"模型 '{model_name}' 缺少必要配置: {field}")

        # 创建ModelConfig对象
        return LLMModelConfig(
            api_base=model_config["api_base"],
            api_key=model_config["api_key"],
            model_name=model_config["model_name"],
        )

    def list_available_models(self) -> List[str]:
        """
        获取所有可用的模型名称列表

        Returns:
            List[str]: 可用模型名称列表
        """
        if "models" not in self._config_cache:
            return []
        return list(self._config_cache["models"].keys())

    def reload_config(self) -> None:
        """重新加载配置文件"""
        self._config_cache = None
        self._load_config()

    def validate_config(self) -> Dict[str, List[str]]:
        """
        验证配置文件的完整性

        Returns:
            Dict[str, List[str]]: 验证结果，键为模型名，值为错误列表
        """
        errors = {}

        if "models" not in self._config_cache:
            errors["global"] = ["缺少models配置"]
            return errors

        required_fields = ["api_base", "api_key", "model_name"]

        for model_name, model_config in self._config_cache["models"].items():
            model_errors = []

            for field in required_fields:
                if field not in model_config or not model_config[field]:
                    model_errors.append(f"缺少必要字段: {field}")

            if model_errors:
                errors[model_name] = model_errors

        return errors


def test_simple_config():
    """测试简化后的配置管理器功能"""
    try:
        config_manager = LLMConfigManager()

        print("=== 测试配置管理器 ===")

        # 测试获取可用模型列表
        models = config_manager.list_available_models()
        print(f"可用模型: {models}")

        # 测试获取默认模型配置
        config = config_manager.get_model_config()
        print("默认模型配置:")
        print(f"  - API Base: {config.api_base}")
        print(f"  - API Key: {config.api_key[:10]}...")  # 只显示前10个字符
        print(f"  - Model Name: {config.model_name}")

        # 测试获取指定模型配置
        if "deepseek" in models:
            deepseek_config = config_manager.get_model_config("deepseek")
            print("DeepSeek模型配置:")
            print(f"  - API Base: {deepseek_config.api_base}")
            print(f"  - API Key: {deepseek_config.api_key[:10]}...")
            print(f"  - Model Name: {deepseek_config.model_name}")

        # 测试配置验证
        validation_errors = config_manager.validate_config()
        if validation_errors:
            print(f"配置验证错误: {validation_errors}")
        else:
            print("✅ 配置验证通过！")

        print("✅ 所有测试通过！")

    except Exception as e:
        print(f"❌ 测试失败: {e}")


if __name__ == "__main__":
    test_simple_config()
