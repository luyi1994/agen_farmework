"""快速测试：验证 107 个教育技能是否能全部加载成功"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from skills.education.loader import load_education_skills

edu_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'claude-education-skills'))
print(f'Education skills dir: {edu_dir}')
print(f'Exists: {os.path.isdir(edu_dir)}')

count = load_education_skills(edu_dir)
print(f'Loaded: {count} education skills')

# 验证注册表
from skills.registry import get_skill_registry
registry = get_skill_registry()
all_skills = registry.get_all_schemas()
print(f'Registry total schemas: {len(all_skills)}')

# 列出所有已加载的教育技能名
for s in all_skills:
    print(f'  - {s["name"]}')
