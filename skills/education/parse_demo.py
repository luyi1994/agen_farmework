"""
演示：如何从 .md 文件中读取并解析所有教育技能
运行：python -m skills.education.parse_demo
"""

import os
import re
import yaml
from pathlib import Path


# ─── 第一步：解析单个 .md 文件 ──────────────────────────────

def parse_single_skill(filepath: str) -> dict:
    """
    输入：一个 .md 文件路径
    输出：结构化的技能字典

    .md 文件结构：
    ---
    YAML 元数据（skill_id, input_schema, chains_well_with 等）
    ---
    # 标题
    ## What This Skill Does
    ## Evidence Foundation
    ## Input Schema
    ## Prompt
    ```
    实际 prompt 模板（含 {{变量}} 占位符）
    ```
    ## Example Output
    ## Known Limitations
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # ① 用正则分离 YAML 头部 和 Markdown 正文
    #    文件以 --- 开头，第二个 --- 结束 YAML 区域
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
    if not match:
        raise ValueError(f"无法解析 YAML 头部: {filepath}")

    yaml_text = match.group(1)   # YAML 部分
    body = match.group(2)        # Markdown 正文

    # ② 解析 YAML → Python dict
    meta = yaml.safe_load(yaml_text)

    # ③ 从正文中提取 prompt 模板（在 ## Prompt 下的 ``` 代码块中）
    prompt_match = re.search(r'## Prompt\s*\n+```\s*\n(.*?)```', body, re.DOTALL)
    prompt_template = prompt_match.group(1).strip() if prompt_match else ""

    # ④ 将 YAML 的 input_schema 转为 JSON Schema（agent 框架使用的格式）
    parameters = convert_to_json_schema(meta.get("input_schema", {}))

    return {
        "skill_id": meta.get("skill_id", ""),
        "skill_name": meta.get("skill_name", ""),
        "domain": meta.get("domain", ""),
        "evidence_strength": meta.get("evidence_strength", ""),
        "evidence_sources": meta.get("evidence_sources", []),
        "chains_well_with": meta.get("chains_well_with", []),
        "tags": meta.get("tags", []),
        "parameters": parameters,        # JSON Schema 格式
        "prompt_template": prompt_template,  # 可直接发给 LLM 的模板
        "source_file": filepath,
    }


def convert_to_json_schema(input_schema: dict) -> dict:
    """
    转换：
      YAML 格式：                          JSON Schema 格式：
      required:                            {
        - field: "topics"                    "type": "object",
          type: "array"                      "properties": {
          description: "..."                   "topics": {"type": "array", "description": "..."},
      optional:                                "assessment_date": {"type": "string", "description": "..."}
        - field: "assessment_date"           },
          type: "string"                     "required": ["topics"]
          description: "..."               }
    """
    properties = {}
    required = []

    for field_def in input_schema.get("required", []):
        name = field_def["field"]
        required.append(name)
        properties[name] = {
            "type": field_def.get("type", "string"),
            "description": field_def.get("description", ""),
        }

    for field_def in input_schema.get("optional", []):
        name = field_def["field"]
        properties[name] = {
            "type": field_def.get("type", "string"),
            "description": field_def.get("description", ""),
        }

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


# ─── 第二步：扫描整个目录，批量加载 ──────────────────────────

def load_all_education_skills(skills_dir: str) -> list[dict]:
    """
    扫描 claude-education-skills/ 目录结构：

    claude-education-skills/
    ├── README.md                    ← 跳过（非技能文件）
    ├── ARCHITECTURE.md              ← 跳过
    ├── memory-learning-science/     ← domain 子目录
    │   ├── spaced-practice-scheduler.md      ← ✅ 技能文件
    │   ├── retrieval-practice-generator.md   ← ✅ 技能文件
    │   └── ...
    ├── ai-learning-science/
    │   ├── adaptive-hint-sequence-designer.md ← ✅ 技能文件
    │   └── ...
    └── ... (14 个 domain 子目录)

    规则：只处理子目录中的 .md 文件，跳过根目录的文档文件
    """
    skills_path = Path(skills_dir)

    # 根目录的文档文件，不是技能
    skip_files = {
        "README.md", "ARCHITECTURE.md", "EVIDENCE.md",
        "EXCLUSIONS.md", "IMPLEMENTATIONS.md", "CONTRIBUTING.md",
    }

    all_skills = []

    for md_file in sorted(skills_path.rglob("*.md")):
        # 跳过根目录文件
        if md_file.parent == skills_path:
            continue
        # 跳过文档文件（以防子目录也有）
        if md_file.name in skip_files:
            continue
        # 跳过 original-frameworks 下非技能文件等边缘情况
        try:
            skill = parse_single_skill(str(md_file))
            all_skills.append(skill)
        except Exception as e:
            print(f"  ⚠ 跳过 {md_file.name}: {e}")

    return all_skills


# ─── 运行演示 ─────────────────────────────────────────────

if __name__ == "__main__":
    SKILLS_DIR = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "claude-education-skills"
    )
    SKILLS_DIR = os.path.abspath(SKILLS_DIR)

    print(f"扫描目录: {SKILLS_DIR}\n")

    skills = load_all_education_skills(SKILLS_DIR)

    # ── 汇总统计 ──
    print(f"{'='*60}")
    print(f"总计加载: {len(skills)} 个教育技能")
    print(f"{'='*60}\n")

    # ── 按 domain 分组统计 ──
    domains = {}
    for s in skills:
        d = s["domain"]
        domains.setdefault(d, []).append(s)

    print("按领域分布:")
    for domain, skill_list in sorted(domains.items()):
        print(f"  {domain}: {len(skill_list)} 个")
        for sk in skill_list:
            evidence = sk["evidence_strength"]
            chains = len(sk["chains_well_with"])
            params = sk["parameters"]
            required_count = len(params.get("required", []))
            optional_count = len(params["properties"]) - required_count
            print(f"    - {sk['skill_name']}")
            print(f"      证据: {evidence} | 必填参数: {required_count} | 可选参数: {optional_count} | 可链接: {chains}")

    # ── 单个技能详细展示 ──
    print(f"\n{'='*60}")
    print("示例：第一个技能的完整解析结果")
    print(f"{'='*60}\n")

    example = skills[0]
    print(f"skill_id:          {example['skill_id']}")
    print(f"skill_name:        {example['skill_name']}")
    print(f"domain:            {example['domain']}")
    print(f"evidence_strength: {example['evidence_strength']}")
    print(f"evidence_sources:  {len(example['evidence_sources'])} 条")
    for src in example["evidence_sources"]:
        print(f"  - {src}")
    print(f"chains_well_with:  {example['chains_well_with']}")
    print(f"tags:              {example['tags']}")
    print(f"\nJSON Schema 参数:")
    import json
    print(json.dumps(example["parameters"], indent=2, ensure_ascii=False))
    print(f"\nPrompt 模板 (前 300 字符):")
    print(example["prompt_template"][:300] + "...")
