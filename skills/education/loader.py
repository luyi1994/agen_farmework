import re
import yaml
from pathlib import Path
from skills.education.skill import EducationSkill
from skills.registry import get_skill_registry
from utils.logger import logger


def parse_education_skill(filepath: str) -> EducationSkill:
    """
    解析单个教育技能 .md 文件，返回 EducationSkill 实例。

    .md 文件格式：
    ---
    skill_id: "domain/skill-name"
    input_schema:
      required:
        - field: "xxx"
          type: "string"
          description: "..."
      optional: [...]
    chains_well_with: [...]
    ---
    # 标题
    ## Prompt
    ```
    prompt 模板（含 {{变量}} 占位符）
    ```
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 分离 YAML 头部和正文
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
    if not match:
        raise ValueError(f"无法解析 YAML 头部: {filepath}")

    yaml_text = match.group(1)
    body = match.group(2)

    meta = yaml.safe_load(yaml_text)

    # 提取 prompt 模板
    prompt_match = re.search(r"## Prompt\s*\n+```\s*\n(.*?)```", body, re.DOTALL)
    prompt_template = prompt_match.group(1).strip() if prompt_match else ""

    # 转换 input_schema → JSON Schema
    parameters = _convert_input_schema(meta.get("input_schema", {}))

    # 生成 agent 注册名称：edu__domain__skill-name
    skill_id = meta.get("skill_id", "")
    name = f"edu__{skill_id.replace('/', '__')}"

    return EducationSkill(
        name=name,
        description=meta.get("skill_name", ""),
        parameters=parameters,
        prompt_template=prompt_template,
        evidence_strength=meta.get("evidence_strength", "unknown"),
        evidence_sources=meta.get("evidence_sources", []),
        chains_well_with=meta.get("chains_well_with", []),
        domain=meta.get("domain", ""),
        skill_id=skill_id,
        tags=meta.get("tags", []),
    )


def _convert_input_schema(schema: dict) -> dict:
    """
    YAML input_schema 转 JSON Schema。

    输入格式:
      required:
        - field: "topics"
          type: "array"
          description: "List of topics"
      optional:
        - field: "assessment_date"
          type: "string"
          description: "..."

    输出格式:
      {
        "type": "object",
        "properties": {
          "topics": {"type": "array", "description": "..."},
          "assessment_date": {"type": "string", "description": "..."}
        },
        "required": ["topics"]
      }
    """
    properties = {}
    required = []

    for field_def in schema.get("required", []):
        field_name = field_def["field"]
        required.append(field_name)
        properties[field_name] = {
            "type": field_def.get("type", "string"),
            "description": field_def.get("description", ""),
        }

    for field_def in schema.get("optional", []):
        field_name = field_def["field"]
        properties[field_name] = {
            "type": field_def.get("type", "string"),
            "description": field_def.get("description", ""),
        }

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def load_education_skills(skills_dir: str) -> int:
    """
    扫描教育技能目录，解析所有子目录中的 .md 文件，
    注册到全局 SkillRegistry。返回成功加载的数量。
    """
    registry = get_skill_registry()
    loaded = 0
    skills_path = Path(skills_dir)

    if not skills_path.is_dir():
        logger.warning(f"教育技能目录不存在: {skills_dir}")
        return 0

    # 根目录文档文件，不是技能
    skip_files = {
        "README.md", "ARCHITECTURE.md", "EVIDENCE.md",
        "EXCLUSIONS.md", "IMPLEMENTATIONS.md", "CONTRIBUTING.md",
    }

    for md_file in sorted(skills_path.rglob("*.md")):
        # 只处理子目录中的文件
        if md_file.parent == skills_path:
            continue
        if md_file.name in skip_files:
            continue

        try:
            skill = parse_education_skill(str(md_file))
            registry.register_instance(skill)
            loaded += 1
        except Exception as e:
            logger.warning(f"教育技能加载失败 [{md_file.name}]: {e}")

    logger.info(f"教育技能加载完成: {loaded}/{loaded} 个")
    return loaded
