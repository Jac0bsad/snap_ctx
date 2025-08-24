from typing import Dict, List, Optional, NamedTuple, Any
from pathlib import Path
import yaml


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
        self.config_path = Path(config_path)
        self._config_cache: dict = None
        self._load_config()

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
