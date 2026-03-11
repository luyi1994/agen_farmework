"""
教育技能集成测试。

运行方式：
    cd agent_framework
    pytest tests/test_education_skills.py -v
"""

import pytest
import asyncio
import os
import sys
import re
import tempfile
import textwrap

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skills.education.loader import parse_education_skill, load_education_skills, _convert_input_schema
from skills.education.skill import EducationSkill
from skills.registry import SkillRegistry
from skills.base import SkillResult

# 教育技能目录（相对于 agent_framework）
EDU_SKILLS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "claude-education-skills")
)


# ─── 辅助：创建临时 .md 技能文件 ─────────────────────────────

SAMPLE_SKILL_MD = textwrap.dedent("""\
    ---
    skill_id: "test-domain/sample-skill"
    skill_name: "Sample Test Skill"
    domain: "test-domain"
    version: "1.0"
    evidence_strength: "strong"
    evidence_sources:
      - "Author A (2020) — Finding A"
      - "Author B (2021) — Finding B"
    input_schema:
      required:
        - field: "topic"
          type: "string"
          description: "The main topic"
        - field: "level"
          type: "string"
          description: "Student level"
      optional:
        - field: "context"
          type: "string"
          description: "Additional context"
    output_schema:
      type: "object"
      fields:
        - field: "result"
          type: "string"
          description: "The generated output"
    chains_well_with:
      - "other-skill-a"
      - "other-skill-b"
    teacher_time: "3 minutes"
    tags: ["test", "sample"]
    ---

    # Sample Test Skill

    ## What This Skill Does

    This is a test skill for unit testing.

    ## Prompt

    ```
    You are an expert in {{topic}}.

    Design a lesson for {{level}} students.

    Optional context: {{context}}

    Return a structured lesson plan.
    ```

    ## Known Limitations

    This is a test skill.
""")


# ═══════════════════════════════════════════════════════════════
# 1. YAML 解析测试
# ═══════════════════════════════════════════════════════════════

class TestYamlParsing:
    """测试 .md 文件的 YAML 头部解析"""

    def _write_temp_skill(self, content: str) -> str:
        """写入临时 .md 文件并返回路径"""
        fd, path = tempfile.mkstemp(suffix=".md")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_parse_yaml_header(self):
        """能正确解析 YAML 头部的所有字段"""
        path = self._write_temp_skill(SAMPLE_SKILL_MD)
        try:
            skill = parse_education_skill(path)
            assert skill.skill_id == "test-domain/sample-skill"
            assert skill.domain == "test-domain"
            assert skill.evidence_strength == "strong"
            assert len(skill.evidence_sources) == 2
            assert "Author A" in skill.evidence_sources[0]
        finally:
            os.unlink(path)

    def test_parse_chains_well_with(self):
        """能正确解析 chains_well_with 列表"""
        path = self._write_temp_skill(SAMPLE_SKILL_MD)
        try:
            skill = parse_education_skill(path)
            assert skill.chains_well_with == ["other-skill-a", "other-skill-b"]
        finally:
            os.unlink(path)

    def test_parse_tags(self):
        """能正确解析 tags"""
        path = self._write_temp_skill(SAMPLE_SKILL_MD)
        try:
            skill = parse_education_skill(path)
            assert skill.tags == ["test", "sample"]
        finally:
            os.unlink(path)

    def test_parse_invalid_file_raises(self):
        """没有 YAML 头部的文件应抛出 ValueError"""
        path = self._write_temp_skill("# No YAML header\nJust markdown.")
        try:
            with pytest.raises(ValueError, match="无法解析"):
                parse_education_skill(path)
        finally:
            os.unlink(path)


# ═══════════════════════════════════════════════════════════════
# 2. input_schema → JSON Schema 转换测试
# ═══════════════════════════════════════════════════════════════

class TestSchemaConversion:
    """测试 YAML input_schema 到 JSON Schema 的转换"""

    def test_required_fields(self):
        """required 字段正确映射"""
        schema = _convert_input_schema({
            "required": [
                {"field": "topics", "type": "array", "description": "Topic list"},
                {"field": "timeline", "type": "string", "description": "Time period"},
            ],
            "optional": [],
        })
        assert schema["type"] == "object"
        assert "topics" in schema["properties"]
        assert schema["properties"]["topics"]["type"] == "array"
        assert schema["required"] == ["topics", "timeline"]

    def test_optional_fields(self):
        """optional 字段映射到 properties 但不在 required 中"""
        schema = _convert_input_schema({
            "required": [
                {"field": "topic", "type": "string", "description": "Main topic"},
            ],
            "optional": [
                {"field": "difficulty", "type": "string", "description": "Difficulty level"},
            ],
        })
        assert "difficulty" in schema["properties"]
        assert "difficulty" not in schema["required"]
        assert schema["required"] == ["topic"]

    def test_empty_schema(self):
        """空 schema 返回合法的空 JSON Schema"""
        schema = _convert_input_schema({})
        assert schema == {
            "type": "object",
            "properties": {},
            "required": [],
        }


# ═══════════════════════════════════════════════════════════════
# 3. Prompt 模板提取测试
# ═══════════════════════════════════════════════════════════════

class TestPromptExtraction:
    """测试从 .md 正文中提取 prompt 模板"""

    def _write_temp_skill(self, content: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".md")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_extract_prompt_template(self):
        """能正确提取 ## Prompt 下代码块中的模板"""
        path = self._write_temp_skill(SAMPLE_SKILL_MD)
        try:
            skill = parse_education_skill(path)
            assert "You are an expert in {{topic}}" in skill.prompt_template
            assert "{{level}}" in skill.prompt_template
            assert "{{context}}" in skill.prompt_template
        finally:
            os.unlink(path)

    def test_prompt_placeholders_detected(self):
        """能检测到 prompt 中所有的 {{变量}} 占位符"""
        path = self._write_temp_skill(SAMPLE_SKILL_MD)
        try:
            skill = parse_education_skill(path)
            placeholders = re.findall(r"\{\{(\w+)\}\}", skill.prompt_template)
            assert set(placeholders) == {"topic", "level", "context"}
        finally:
            os.unlink(path)


# ═══════════════════════════════════════════════════════════════
# 4. EducationSkill 实例行为测试
# ═══════════════════════════════════════════════════════════════

class TestEducationSkillInstance:
    """测试 EducationSkill 实例的方法和属性"""

    def _make_skill(self) -> EducationSkill:
        return EducationSkill(
            name="edu__test-domain__sample-skill",
            description="Sample Test Skill",
            parameters={
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Main topic"},
                    "level": {"type": "string", "description": "Student level"},
                    "context": {"type": "string", "description": "Extra context"},
                },
                "required": ["topic", "level"],
            },
            prompt_template="You are an expert in {{topic}}. Level: {{level}}. Context: {{context}}.",
            evidence_strength="strong",
            evidence_sources=["Source A", "Source B"],
            chains_well_with=["other-skill"],
            domain="test-domain",
            skill_id="test-domain/sample-skill",
            tags=["test"],
        )

    def test_fill_template_all_provided(self):
        """所有参数都提供时正确填充"""
        skill = self._make_skill()
        result = skill._fill_template({
            "topic": "Mathematics",
            "level": "Year 8",
            "context": "Algebra unit",
        })
        assert "You are an expert in Mathematics" in result
        assert "Level: Year 8" in result
        assert "Context: Algebra unit" in result

    def test_fill_template_optional_missing(self):
        """未提供的可选参数填充为 'not provided'"""
        skill = self._make_skill()
        result = skill._fill_template({
            "topic": "Science",
            "level": "Year 10",
        })
        assert "Context: not provided" in result

    def test_fill_template_list_input(self):
        """列表类型输入转为逗号分隔字符串"""
        skill = self._make_skill()
        result = skill._fill_template({
            "topic": ["Cells", "DNA", "Evolution"],
            "level": "Year 9",
        })
        assert "Cells, DNA, Evolution" in result

    def test_to_tool_schema(self):
        """生成的 Tool Schema 包含正确的名称和证据标签"""
        skill = self._make_skill()
        schema = skill.to_tool_schema()
        assert schema["name"] == "edu__test-domain__sample-skill"
        assert "[edu|strong]" in schema["description"]
        assert "topic" in schema["parameters"]["properties"]

    def test_name_format(self):
        """技能名称遵循 edu__domain__skill-name 格式"""
        skill = self._make_skill()
        assert skill.name.startswith("edu__")
        parts = skill.name.split("__")
        assert len(parts) == 3


# ═══════════════════════════════════════════════════════════════
# 5. EducationSkill.run() 异步执行测试
# ═══════════════════════════════════════════════════════════════

class TestEducationSkillRun:
    """测试 EducationSkill 的 run() 方法（mock LLM）"""

    @staticmethod
    def _setup_mocks(mock_provider):
        """
        注入 mock 的 llm 和 langchain_core 模块，
        绕过未安装 langchain_community / langchain_core 的环境。
        返回需要还原的 original modules dict。
        """
        from unittest.mock import MagicMock

        originals = {}
        modules_to_mock = ["llm", "langchain_core", "langchain_core.messages"]

        for mod_name in modules_to_mock:
            originals[mod_name] = sys.modules.get(mod_name)

        # mock llm module
        mock_llm_module = MagicMock()
        mock_llm_module.get_llm_provider = MagicMock(return_value=mock_provider)
        sys.modules["llm"] = mock_llm_module

        # mock langchain_core.messages.HumanMessage
        mock_lc_core = MagicMock()
        mock_lc_messages = MagicMock()
        mock_lc_messages.HumanMessage = lambda content: MagicMock(content=content)
        sys.modules["langchain_core"] = mock_lc_core
        sys.modules["langchain_core.messages"] = mock_lc_messages

        return originals

    @staticmethod
    def _restore_mocks(originals):
        for mod_name, original in originals.items():
            if original is not None:
                sys.modules[mod_name] = original
            else:
                sys.modules.pop(mod_name, None)

    @pytest.mark.asyncio
    async def test_run_success(self):
        """run() 成功调用 LLM 并返回 SkillResult"""
        from unittest.mock import MagicMock

        skill = EducationSkill(
            name="edu__test__skill",
            description="Test",
            parameters={"type": "object", "properties": {}, "required": []},
            prompt_template="Tell me about {{topic}}.",
            evidence_strength="strong",
            domain="test",
            skill_id="test/skill",
            tags=[],
            chains_well_with=[],
            evidence_sources=[],
        )

        mock_response = MagicMock()
        mock_response.content = "This is the LLM output about Biology."

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response

        mock_provider = MagicMock()
        mock_provider.get_model.return_value = mock_llm

        originals = self._setup_mocks(mock_provider)
        try:
            result = await skill.run(topic="Biology")
        finally:
            self._restore_mocks(originals)

        assert result.success is True
        assert "Biology" in result.data["output"]
        assert result.data["skill_id"] == "test/skill"
        assert result.data["evidence_strength"] == "strong"
        assert result.metadata["domain"] == "test"

    @pytest.mark.asyncio
    async def test_run_empty_prompt(self):
        """空 prompt 模板应返回失败"""
        skill = EducationSkill(
            name="edu__empty__skill",
            description="Empty",
            parameters={"type": "object", "properties": {}, "required": []},
            prompt_template="",
            evidence_strength="unknown",
            domain="empty",
            skill_id="empty/skill",
            tags=[],
            chains_well_with=[],
            evidence_sources=[],
        )
        result = await skill.run()
        assert result.success is False
        assert "prompt 模板为空" in result.error

    @pytest.mark.asyncio
    async def test_run_llm_failure(self):
        """LLM 调用失败时返回 error"""
        from unittest.mock import MagicMock

        skill = EducationSkill(
            name="edu__fail__skill",
            description="Fail",
            parameters={"type": "object", "properties": {}, "required": []},
            prompt_template="Do something about {{topic}}.",
            evidence_strength="moderate",
            domain="fail",
            skill_id="fail/skill",
            tags=[],
            chains_well_with=[],
            evidence_sources=[],
        )

        mock_provider = MagicMock()
        mock_provider.get_model.side_effect = RuntimeError("LLM unavailable")

        originals = self._setup_mocks(mock_provider)
        try:
            result = await skill.run(topic="test")
        finally:
            self._restore_mocks(originals)

        assert result.success is False
        assert "LLM unavailable" in result.error


# ═══════════════════════════════════════════════════════════════
# 6. SkillRegistry 集成测试
# ═══════════════════════════════════════════════════════════════

class TestRegistryIntegration:
    """测试教育技能注册到 SkillRegistry"""

    def test_register_instance(self):
        """register_instance 能正确注册实例"""
        registry = SkillRegistry()
        skill = EducationSkill(
            name="edu__test__reg",
            description="Registry test",
            parameters={"type": "object", "properties": {}, "required": []},
            prompt_template="Hello {{name}}",
            evidence_strength="moderate",
            domain="test",
            skill_id="test/reg",
            tags=[],
            chains_well_with=[],
            evidence_sources=[],
        )
        registry.register_instance(skill)
        assert "edu__test__reg" in registry.list_skills()
        assert registry.get("edu__test__reg") is skill

    def test_schemas_include_edu_skills(self):
        """get_all_schemas 包含教育技能的 schema"""
        registry = SkillRegistry()
        skill = EducationSkill(
            name="edu__test__schema",
            description="Schema test",
            parameters={
                "type": "object",
                "properties": {"x": {"type": "string", "description": "input"}},
                "required": ["x"],
            },
            prompt_template="{{x}}",
            evidence_strength="strong",
            domain="test",
            skill_id="test/schema",
            tags=[],
            chains_well_with=[],
            evidence_sources=[],
        )
        registry.register_instance(skill)
        schemas = registry.get_all_schemas()
        edu_schema = next(s for s in schemas if s["name"] == "edu__test__schema")
        assert "[edu|strong]" in edu_schema["description"]
        assert "x" in edu_schema["parameters"]["properties"]

    @pytest.mark.asyncio
    async def test_execute_via_registry(self):
        """通过 registry.execute 调用教育技能"""
        from unittest.mock import patch, MagicMock

        registry = SkillRegistry()
        skill = EducationSkill(
            name="edu__test__exec",
            description="Exec test",
            parameters={"type": "object", "properties": {}, "required": []},
            prompt_template="About {{topic}}.",
            evidence_strength="strong",
            domain="test",
            skill_id="test/exec",
            tags=[],
            chains_well_with=[],
            evidence_sources=[],
        )
        registry.register_instance(skill)

        mock_response = MagicMock()
        mock_response.content = "LLM response here."
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response
        mock_provider = MagicMock()
        mock_provider.get_model.return_value = mock_llm

        # 注入 mock llm 模块
        originals = TestEducationSkillRun._setup_mocks(mock_provider)
        try:
            result = await registry.execute("edu__test__exec", topic="math")
        finally:
            TestEducationSkillRun._restore_mocks(originals)

        assert result.success is True
        assert result.data["output"] == "LLM response here."


# ═══════════════════════════════════════════════════════════════
# 7. 真实文件批量加载测试
# ═══════════════════════════════════════════════════════════════

class TestRealFilesLoading:
    """测试从真实 claude-education-skills 目录加载（需要目录存在）"""

    @pytest.fixture(autouse=True)
    def check_edu_dir(self):
        if not os.path.isdir(EDU_SKILLS_DIR):
            pytest.skip(f"教育技能目录不存在: {EDU_SKILLS_DIR}")

    def test_load_all_skills_count(self):
        """能加载 100+ 个技能"""
        registry = SkillRegistry()
        # 临时替换全局 registry
        from skills import registry as reg_module
        original = reg_module._global_skill_registry
        reg_module._global_skill_registry = registry
        try:
            count = load_education_skills(EDU_SKILLS_DIR)
            assert count >= 100, f"预期 100+ 个技能，实际 {count}"
        finally:
            reg_module._global_skill_registry = original

    def test_all_skills_have_required_fields(self):
        """每个加载的技能都有 skill_id、domain、prompt_template"""
        registry = SkillRegistry()
        from skills import registry as reg_module
        original = reg_module._global_skill_registry
        reg_module._global_skill_registry = registry
        try:
            load_education_skills(EDU_SKILLS_DIR)
            for name, skill in registry._skills.items():
                assert skill.skill_id, f"{name}: skill_id 为空"
                assert skill.domain, f"{name}: domain 为空"
                assert skill.prompt_template, f"{name}: prompt_template 为空"
                assert skill.evidence_strength in (
                    "strong", "moderate", "emerging", "original"
                ), f"{name}: evidence_strength 无效: {skill.evidence_strength}"
        finally:
            reg_module._global_skill_registry = original

    def test_all_skills_have_valid_parameters(self):
        """每个技能的 parameters 都是合法的 JSON Schema"""
        registry = SkillRegistry()
        from skills import registry as reg_module
        original = reg_module._global_skill_registry
        reg_module._global_skill_registry = registry
        try:
            load_education_skills(EDU_SKILLS_DIR)
            for name, skill in registry._skills.items():
                params = skill.parameters
                assert params["type"] == "object", f"{name}: type 不是 object"
                assert "properties" in params, f"{name}: 缺少 properties"
                assert "required" in params, f"{name}: 缺少 required"
                # required 中的字段必须在 properties 中
                for req in params["required"]:
                    assert req in params["properties"], (
                        f"{name}: required 字段 '{req}' 不在 properties 中"
                    )
        finally:
            reg_module._global_skill_registry = original

    def test_specific_skill_parsing(self):
        """精确验证一个已知技能的解析结果"""
        filepath = os.path.join(
            EDU_SKILLS_DIR,
            "memory-learning-science",
            "spaced-practice-scheduler.md",
        )
        if not os.path.isfile(filepath):
            pytest.skip("spaced-practice-scheduler.md 不存在")

        skill = parse_education_skill(filepath)

        # 元数据
        assert skill.skill_id == "memory-learning-science/spaced-practice-scheduler"
        assert skill.domain == "memory-learning-science"
        assert skill.evidence_strength == "strong"
        assert len(skill.evidence_sources) == 5
        assert any("Cepeda" in s for s in skill.evidence_sources)

        # 参数
        assert "topics" in skill.parameters["required"]
        assert "timeline" in skill.parameters["required"]
        assert "lessons_per_week" in skill.parameters["required"]
        assert "assessment_date" in skill.parameters["properties"]
        assert "assessment_date" not in skill.parameters["required"]

        # Prompt 模板
        assert "{{topics}}" in skill.prompt_template
        assert "{{timeline}}" in skill.prompt_template
        assert "{{lessons_per_week}}" in skill.prompt_template
        assert "Ebbinghaus" in skill.prompt_template

        # 链接关系
        assert "retrieval-practice-generator" in skill.chains_well_with

        # 名称
        assert skill.name == "edu__memory-learning-science__spaced-practice-scheduler"

    def test_domains_coverage(self):
        """14 个领域都有技能被加载"""
        registry = SkillRegistry()
        from skills import registry as reg_module
        original = reg_module._global_skill_registry
        reg_module._global_skill_registry = registry
        try:
            load_education_skills(EDU_SKILLS_DIR)
            domains = set()
            for skill in registry._skills.values():
                if hasattr(skill, "domain") and skill.domain:
                    domains.add(skill.domain)
            assert len(domains) >= 14, f"预期 14 个领域，实际 {len(domains)}: {domains}"
        finally:
            reg_module._global_skill_registry = original

    def test_nonexistent_directory(self):
        """不存在的目录应返回 0，不报错"""
        count = load_education_skills("/nonexistent/path/that/does/not/exist")
        assert count == 0


# ═══════════════════════════════════════════════════════════════
# 8. 临时目录批量加载测试（不依赖真实文件）
# ═══════════════════════════════════════════════════════════════

class TestLoaderWithTempDir:
    """使用临时目录模拟教育技能目录结构"""

    def _create_temp_skills_dir(self, tmp_path, num_skills=3):
        """在 tmp_path 下创建模拟的教育技能目录"""
        domain_dir = tmp_path / "test-domain"
        domain_dir.mkdir()

        for i in range(num_skills):
            skill_md = domain_dir / f"skill-{i}.md"
            skill_md.write_text(textwrap.dedent(f"""\
                ---
                skill_id: "test-domain/skill-{i}"
                skill_name: "Test Skill {i}"
                domain: "test-domain"
                version: "1.0"
                evidence_strength: "strong"
                evidence_sources:
                  - "Test source"
                input_schema:
                  required:
                    - field: "input_{i}"
                      type: "string"
                      description: "Input for skill {i}"
                  optional: []
                chains_well_with: []
                tags: ["test"]
                ---

                # Test Skill {i}

                ## Prompt

                ```
                You are testing skill {i}. Input: {{{{input_{i}}}}}
                ```
            """), encoding="utf-8")

        # 也在根目录放一个 README.md（应该被跳过）
        (tmp_path / "README.md").write_text("# Test README", encoding="utf-8")

        return str(tmp_path)

    def test_load_from_temp_dir(self, tmp_path):
        """从临时目录加载技能"""
        skills_dir = self._create_temp_skills_dir(tmp_path, num_skills=5)
        registry = SkillRegistry()

        from skills import registry as reg_module
        original = reg_module._global_skill_registry
        reg_module._global_skill_registry = registry
        try:
            count = load_education_skills(skills_dir)
            assert count == 5
            assert len(registry.list_skills()) == 5
        finally:
            reg_module._global_skill_registry = original

    def test_root_readme_skipped(self, tmp_path):
        """根目录的 README.md 不会被当作技能加载"""
        skills_dir = self._create_temp_skills_dir(tmp_path, num_skills=2)
        registry = SkillRegistry()

        from skills import registry as reg_module
        original = reg_module._global_skill_registry
        reg_module._global_skill_registry = registry
        try:
            count = load_education_skills(skills_dir)
            names = registry.list_skills()
            assert not any("readme" in n.lower() for n in names)
        finally:
            reg_module._global_skill_registry = original
