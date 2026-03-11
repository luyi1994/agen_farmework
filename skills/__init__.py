from .registry import SkillRegistry, get_skill_registry
from .base import BaseSkill, SkillResult


def load_all_skills() -> None:
    """启动时自动注册所有内置 Skill + 教育技能"""
    from skills.research.skill import ResearchSkill
    from skills.summarize.skill import SummarizeSkill
    from skills.data_analysis.skill import DataAnalysisSkill
    from skills.write_report.skill import WriteReportSkill

    registry = get_skill_registry()
    for cls in [ResearchSkill, SummarizeSkill, DataAnalysisSkill, WriteReportSkill]:
        registry.register(cls)

    # 加载教育技能
    import os
    from skills.education.loader import load_education_skills

    edu_skills_dir = os.environ.get(
        "EDUCATION_SKILLS_DIR",
        os.path.join(os.path.dirname(__file__), "..", "..", "claude-education-skills"),
    )
    edu_skills_dir = os.path.abspath(edu_skills_dir)
    if os.path.isdir(edu_skills_dir):
        load_education_skills(edu_skills_dir)


__all__ = ["SkillRegistry", "get_skill_registry", "BaseSkill", "SkillResult", "load_all_skills"]
