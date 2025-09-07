#!/usr/bin/env python3
"""
OneSquare Architecture Diagram Auto-Updater
MODULE_TRACKER.md를 읽어서 architecture.md의 Mermaid 다이어그램을 자동 업데이트
"""

import re
import json
from datetime import datetime
from pathlib import Path
import sys

class ArchitectureUpdater:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.module_tracker_path = self.project_root / "MODULE_TRACKER.md"
        self.architecture_path = self.project_root / "docs" / "architecture.md"
        self.modules = {
            'core': [],
            'utils': [],
            'features': [],
            'integration': []
        }
        self.dependencies = {}
        
    def parse_module_tracker(self):
        """MODULE_TRACKER.md 파일 파싱"""
        with open(self.module_tracker_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 섹션별로 모듈 추출
        self._parse_section(content, "Core Modules", 'core')
        self._parse_section(content, "Utils Modules", 'utils')
        self._parse_section(content, "Feature Modules", 'features')
        self._parse_section(content, "Integration Modules", 'integration')
        
        print(f"✅ 파싱 완료: {sum(len(v) for v in self.modules.values())} 모듈 발견")
        
    def _parse_section(self, content, section_name, module_type):
        """특정 섹션에서 모듈 정보 추출"""
        pattern = rf"### .* {section_name}.*?\n(.*?)(?=###|\Z)"
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            section_content = match.group(1)
            # 테이블 행 파싱
            rows = re.findall(r'\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]*)\|', section_content)
            
            for row in rows[1:]:  # 헤더 제외
                module_name = row[0].strip().replace('**', '')
                file_path = row[1].strip().replace('`', '')
                status = row[2].strip()
                deps = row[3].strip()
                
                if module_name and '---' not in module_name:
                    module_info = {
                        'name': module_name,
                        'path': file_path,
                        'status': status,
                        'dependencies': deps
                    }
                    self.modules[module_type].append(module_info)
                    
                    # 의존성 매핑
                    if deps and deps != '-':
                        self.dependencies[module_name] = deps.split(', ')
    
    def generate_module_diagram(self):
        """모듈 의존성 다이어그램 생성"""
        diagram = ["```mermaid", "graph LR"]
        
        # Core 모듈
        if self.modules['core']:
            diagram.append('    subgraph Core["🔵 Core Modules"]')
            for module in self.modules['core']:
                safe_name = module['name'].replace('/', '_').replace('.', '_')
                diagram.append(f'        {safe_name}[{module["name"]}]')
            diagram.append('    end')
            diagram.append('')
        
        # Auth 모듈 (별도 처리)
        diagram.append('    subgraph Auth["🟢 Authentication"]')
        diagram.append('        AuthSystem[auth_system]')
        diagram.append('        Decorators[decorators.py]')
        diagram.append('        CustomUser[CustomUser Model]')
        diagram.append('    end')
        diagram.append('')
        
        # Feature 모듈
        if self.modules['features']:
            diagram.append('    subgraph Features["🟡 Feature Modules"]')
            for module in self.modules['features']:
                safe_name = module['name'].replace('/', '_').replace('.', '_')
                diagram.append(f'        {safe_name}[{module["name"]}]')
            diagram.append('    end')
            diagram.append('')
        
        # Integration 모듈
        if self.modules['integration']:
            diagram.append('    subgraph Integration["🟣 Integration"]')
            for module in self.modules['integration']:
                safe_name = module['name'].replace('/', '_').replace('.', '_')
                diagram.append(f'        {safe_name}[{module["name"]}]')
            diagram.append('    end')
            diagram.append('')
        
        # 의존성 화살표 추가
        diagram.append('    %% Dependencies')
        for module, deps in self.dependencies.items():
            safe_module = module.replace('/', '_').replace('.', '_')
            for dep in deps:
                if dep and dep != '-':
                    safe_dep = dep.replace('/', '_').replace('.', '_').strip()
                    diagram.append(f'    {safe_module} --> {safe_dep}')
        
        diagram.append("```")
        return '\n'.join(diagram)
    
    def generate_statistics(self):
        """통계 다이어그램 생성"""
        total_modules = sum(len(v) for v in self.modules.values())
        
        # Pie Chart
        pie_chart = [
            "```mermaid",
            'pie title 모듈 카테고리별 분포',
            f'    "Core Modules" : {len(self.modules["core"])}',
            f'    "Feature Modules" : {len(self.modules["features"])}',
            f'    "Utils Modules" : {len(self.modules["utils"])}',
            f'    "Integration Modules" : {len(self.modules["integration"])}',
            "```"
        ]
        
        return '\n'.join(pie_chart), total_modules
    
    def update_architecture_file(self):
        """architecture.md 파일 업데이트"""
        if not self.architecture_path.exists():
            print(f"⚠️  {self.architecture_path} 파일이 없습니다. 생성합니다...")
            self.architecture_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.architecture_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 모듈 의존성 다이어그램 업데이트
        module_diagram = self.generate_module_diagram()
        pattern = r'## 🔧 모듈 의존성 다이어그램\n\n```mermaid.*?```'
        replacement = f'## 🔧 모듈 의존성 다이어그램\n\n{module_diagram}'
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # 통계 차트 업데이트
        pie_chart, total = self.generate_statistics()
        pattern = r'## 📦 모듈 카테고리 분포\n\n```mermaid.*?```'
        replacement = f'## 📦 모듈 카테고리 분포\n\n{pie_chart}'
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # 마지막 업데이트 시간
        update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = re.sub(
            r'\*마지막 업데이트:.*?\*',
            f'*마지막 업데이트: {update_time}*',
            content
        )
        
        # 파일 저장
        with open(self.architecture_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ architecture.md 업데이트 완료!")
        print(f"📊 총 {total}개 모듈 반영")
        print(f"📅 업데이트 시간: {update_time}")
    
    def generate_summary(self):
        """업데이트 요약 생성"""
        summary = []
        summary.append("\n" + "="*50)
        summary.append("📋 OneSquare Architecture 업데이트 요약")
        summary.append("="*50)
        
        for category, modules in self.modules.items():
            if modules:
                summary.append(f"\n{category.upper()} ({len(modules)}개):")
                for module in modules:
                    status_icon = "✅" if "완료" in module['status'] else "🔄"
                    summary.append(f"  {status_icon} {module['name']}")
        
        summary.append("\n" + "="*50)
        return '\n'.join(summary)
    
    def run(self):
        """메인 실행 함수"""
        print("🚀 OneSquare Architecture Updater 시작...")
        
        try:
            # 1. MODULE_TRACKER.md 파싱
            self.parse_module_tracker()
            
            # 2. architecture.md 업데이트
            self.update_architecture_file()
            
            # 3. 요약 출력
            print(self.generate_summary())
            
            print("\n✨ 모든 작업이 성공적으로 완료되었습니다!")
            return 0
            
        except FileNotFoundError as e:
            print(f"❌ 파일을 찾을 수 없습니다: {e}")
            return 1
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            return 1

def main():
    """스크립트 진입점"""
    updater = ArchitectureUpdater()
    return updater.run()

if __name__ == "__main__":
    sys.exit(main())