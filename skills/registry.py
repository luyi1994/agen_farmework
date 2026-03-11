from typing import Optional, Type
from .base import BaseSkill, SkillResult
from utils.logger import logger


class SkillRegistry:
    """
    Skill 注册中心。
    所有 Skill 对 LLM 暴露为 Tool Schema，LLM 调用时无感知内部几层。
    """

    def __init__(self):
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill_cls: Type[BaseSkill]) -> None:
        instance = skill_cls()
        self._skills[instance.name] = instance
        logger.debug(f"Skill 已注册: {instance.name}")

    def register_instance(self, skill: BaseSkill) -> None:
        """直接注册一个已创建的 Skill 实例（供动态加载场景使用）"""
        self._skills[skill.name] = skill
        logger.debug(f"Skill 已注册(实例): {skill.name}")

    def get(self, name: str) -> Optional[BaseSkill]:
        return self._skills.get(name)

    async def execute(self, name: str, **kwargs) -> SkillResult:
        skill = self.get(name)
        if skill is None:
            return SkillResult(success=False, error=f"Skill '{name}' 不存在")
        logger.info(f"执行 Skill: {name}, args={kwargs}")
        try:
            return await skill.run(**kwargs)
        except Exception as e:
            logger.error(f"Skill '{name}' 执行异常: {e}")
            return SkillResult(success=False, error=str(e))

    def get_all_schemas(self) -> list[dict]:
        """返回所有 Skill 的 Tool Schema，供 LLM 统一识别"""
        return [s.to_tool_schema() for s in self._skills.values()]

    def list_skills(self) -> list[str]:
        return list(self._skills.keys())


# 全局单例
_global_skill_registry = SkillRegistry()


def get_skill_registry() -> SkillRegistry:
    return _global_skill_registry
